"""Bounded BLS CPI transport, capture, replay, and canonicalization."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import (
    Event,
    Observation,
    ObservationVersion,
    RevisionStatus,
    SourceRelease,
    TransportCapture,
)


class BLSQuarantineError(ValueError):
    """The source payload is present but cannot be admitted safely."""


class BLSHTTPError(RuntimeError):
    """A bounded transport failure with no semantic fallback."""


@dataclass(frozen=True)
class CapturedBLSResponse:
    capture: TransportCapture
    raw_bytes: bytes


@dataclass(frozen=True)
class BLSParseResult:
    observations: tuple[Observation, ...]
    quarantined: tuple[dict[str, object], ...]

    @property
    def input_rows(self) -> int:
        """Number of source rows accounted for by admission or quarantine."""

        return len(self.observations) + len(self.quarantined)

    @property
    def admitted_rows(self) -> int:
        return len(self.observations)

    @property
    def reconciled(self) -> bool:
        return self.input_rows == self.admitted_rows + len(self.quarantined)


_SERIES_ID = re.compile(r"^[A-Z]{2}[A-Z0-9]{8,16}$")
_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
_API_HOST = "api.bls.gov"
_PARSER_VERSION = "bls-cpi-v1-observed-results-object"


class _BLSRedirectHandler(HTTPRedirectHandler):
    """Permit only same-host HTTPS redirects before any follow-up request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != "https" or target.hostname != _API_HOST or target.username or target.password:
            raise BLSHTTPError("BLS response redirected to an unallowlisted host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def _iso_max(first: str, second: str) -> str:
    return max(_utc(first), _utc(second)).isoformat().replace("+00:00", "Z")


class BLSClient:
    """Narrowly admitted POST mode for the observed BLS API response grammar."""

    endpoint = _API_URL
    endpoint_id = "bls-cpi-v2"
    source_id = "bls"

    def __init__(self, *, endpoint: str = _API_URL, timeout: float = 15.0, max_retries: int = 2, user_agent: str = "finahinking/0.1 p6.5") -> None:
        parsed_endpoint = urlsplit(endpoint)
        if endpoint != _API_URL or parsed_endpoint.scheme != "https" or parsed_endpoint.hostname != _API_HOST or parsed_endpoint.username or parsed_endpoint.password:
            raise ValueError("BLS endpoint is not allowlisted")
        if timeout <= 0 or timeout > 60:
            raise ValueError("timeout must be between zero and sixty seconds")
        if not isinstance(max_retries, int) or max_retries < 0 or max_retries > 3:
            raise ValueError("max_retries must be bounded")
        if not isinstance(user_agent, str) or not user_agent.strip():
            raise ValueError("user_agent is required")
        self.timeout = float(timeout)
        self.max_retries = max_retries
        self.user_agent = user_agent.strip()
        self._opener = build_opener(_BLSRedirectHandler())

    def validate_request(self, series_ids: list[str] | tuple[str, ...], start_year: int, end_year: int) -> None:
        if not series_ids or len(series_ids) > 50:
            raise ValueError("series count must be between one and fifty")
        if any(not isinstance(series, str) or not _SERIES_ID.fullmatch(series) for series in series_ids):
            raise ValueError("series ids are invalid")
        if not isinstance(start_year, int) or not isinstance(end_year, int) or start_year < 1900 or end_year < start_year:
            raise ValueError("years are invalid")
        if end_year - start_year + 1 > 20:
            raise ValueError("BLS requests may span at most 20 years")
        if self.endpoint != _API_URL:
            raise ValueError("BLS endpoint is not allowlisted")

    def fetch(self, series_ids: list[str] | tuple[str, ...], start_year: int, end_year: int, *, capture_id: str, retrieved_at: str | None = None, first_observed_at: str | None = None) -> CapturedBLSResponse:
        self.validate_request(series_ids, start_year, end_year)
        payload = {"seriesid": list(series_ids), "startyear": str(start_year), "endyear": str(end_year)}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        last_error: Exception | None = None
        retrieval_time = retrieved_at or datetime.now(UTC).isoformat()
        observation_time = first_observed_at or retrieval_time
        for attempt in range(self.max_retries + 1):
            request = Request(self.endpoint, data=encoded, headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": self.user_agent}, method="POST")
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    response_url = urlsplit(response.geturl())
                    if response_url.scheme != "https" or response_url.hostname != _API_HOST:
                        raise BLSHTTPError("BLS response redirected to an unallowlisted host")
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise BLSQuarantineError("BLS payload exceeds capture limit")
                    status = int(getattr(response, "status", 200))
                    headers = {key.lower(): value for key, value in response.headers.items() if key.lower() in {"content-type", "date", "x-rate-limit-remaining"}}
                return self.capture_bytes(raw, capture_id=capture_id, request_payload=payload, retrieved_at=retrieval_time, first_observed_at=observation_time, status=status, relevant_headers=headers)
            except HTTPError as exc:
                if exc.code not in {408, 425, 429} and not 500 <= exc.code <= 599:
                    raise BLSHTTPError(f"BLS transport returned non-retryable HTTP status {exc.code}") from exc
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.05 * (attempt + 1))
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.05 * (attempt + 1))
        raise BLSHTTPError("BLS transport failed after bounded retries") from last_error

    @classmethod
    def capture_bytes(cls, raw_bytes: bytes, *, capture_id: str, request_payload: dict[str, object], retrieved_at: str, first_observed_at: str, status: int = 200, relevant_headers: dict[str, str] | None = None) -> CapturedBLSResponse:
        if not isinstance(raw_bytes, bytes) or not raw_bytes:
            raise ValueError("raw BLS payload is required")
        if len(raw_bytes) > 2_000_000:
            raise ValueError("raw BLS payload exceeds capture limit")
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BLSQuarantineError("BLS payload is not UTF-8") from exc
        request_fingerprint = hashlib.sha256(json.dumps(request_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        capture = TransportCapture(
            capture_id=capture_id,
            source_id=cls.source_id,
            endpoint_id=cls.endpoint_id,
            request_fingerprint=request_fingerprint,
            retrieved_at=retrieved_at,
            first_observed_at=first_observed_at,
            status=status,
            content_type=(relevant_headers or {}).get("content-type", "application/json"),
            relevant_headers=relevant_headers or {},
            raw_artifact_id=f"artifact-{capture_id}",
            payload_hash=hashlib.sha256(raw_bytes).hexdigest(),
            parser_version=_PARSER_VERSION,
            raw_payload=raw_text,
        )
        return CapturedBLSResponse(capture, raw_bytes)

    @classmethod
    def replay(cls, path: str | Path, *, capture_id: str, retrieved_at: str, first_observed_at: str, request_payload: dict[str, object] | None = None) -> CapturedBLSResponse:
        fixture = Path(path)
        if not fixture.is_file():
            raise FileNotFoundError(f"BLS fixture not found: {fixture}")
        raw = fixture.read_bytes()
        payload = request_payload or {"seriesid": [], "startyear": "", "endyear": ""}
        if not payload["seriesid"]:
            try:
                parsed = json.loads(raw)
                payload = {"seriesid": [item["seriesID"] for item in parsed["Results"]["series"]], "startyear": "fixture", "endyear": "fixture"}
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise BLSQuarantineError("BLS fixture shape is invalid") from exc
        return cls.capture_bytes(raw, capture_id=capture_id, request_payload=payload, retrieved_at=retrieved_at, first_observed_at=first_observed_at)


class BLSCPIAdapter:
    """Canonicalize only the admitted BLS CPI POST response grammar."""

    SERIES_DIMENSIONS: ClassVar[dict[str, dict[str, str]]] = {
        "CUUR0000SA0": {"area": "U.S. city average", "item": "All items", "adjustment": "NSA"},
        "CUSR0000SA0": {"area": "U.S. city average", "item": "All items", "adjustment": "SA"},
    }

    @staticmethod
    def parse_capture(capture: TransportCapture, *, release_by_period: dict[str, SourceRelease] | None = None) -> BLSParseResult:
        if not isinstance(capture, TransportCapture):
            raise TypeError("capture must be a TransportCapture")
        if capture.status != 200 or not capture.raw_payload:
            raise BLSQuarantineError("BLS capture is not a successful JSON response")
        try:
            payload = json.loads(capture.raw_payload)
        except json.JSONDecodeError as exc:
            raise BLSQuarantineError("BLS capture is not valid JSON") from exc
        if not isinstance(payload, dict) or payload.get("status") != "REQUEST_SUCCEEDED":
            status = payload.get("status") if isinstance(payload, dict) else None
            raise BLSQuarantineError(f"BLS response status is not admitted: {status!r}")
        results = payload.get("Results")
        if not isinstance(results, dict) or not isinstance(results.get("series"), list):
            raise BLSQuarantineError("BLS Results shape is not the admitted object form")
        observations: list[Observation] = []
        quarantined: list[dict[str, object]] = []
        release_by_period = release_by_period or {}
        seen: set[tuple[str, str]] = set()
        for series in results["series"]:
            if not isinstance(series, dict) or not isinstance(series.get("seriesID"), str) or not isinstance(series.get("data"), list):
                raise BLSQuarantineError("BLS series schema is invalid")
            series_id = series["seriesID"]
            if series_id not in BLSCPIAdapter.SERIES_DIMENSIONS:
                for row in series["data"]:
                    reference_period = ""
                    if isinstance(row, dict):
                        reference_period = f"{row.get('year', '')}-{str(row.get('period', '')).removeprefix('M')}"
                    quarantined.append({"series_id": series_id, "reference_period": reference_period, "reason": "unadmitted_series"})
                continue
            for row in series["data"]:
                if not isinstance(row, dict):
                    raise BLSQuarantineError("BLS observation row is invalid")
                period = f"{row.get('year', '')}-{str(row.get('period', '')).removeprefix('M')}"
                logical_key = (series_id, period)
                footnotes = tuple(BLSCPIAdapter._footnote_texts(row.get("footnotes", [])))
                try:
                    value = float(row.get("value"))
                    if not math.isfinite(value):
                        raise ValueError
                    if not re.fullmatch(r"\d{4}-\d{2}", period) or not 1 <= int(period[-2:]) <= 12:
                        raise ValueError
                except (TypeError, ValueError):
                    quarantined.append({"series_id": series_id, "reference_period": period, "reason": "missing_or_non_numeric_value", "footnotes": list(footnotes)})
                    continue
                if logical_key in seen:
                    quarantined.append({"series_id": series_id, "reference_period": period, "reason": "duplicate_logical_key", "footnotes": list(footnotes)})
                    continue
                seen.add(logical_key)
                release = release_by_period.get(period)
                published_at = release.published_at if release else None
                available_at = None
                if release and release.available_at:
                    available_at = _iso_max(release.available_at, capture.first_observed_at)
                version = ObservationVersion(
                    version_id=f"obs-{series_id.lower()}-{period}-v1",
                    value=value,
                    unit="index",
                    occurred_at=f"{period}-01T00:00:00Z",
                    effective_at=f"{period}-01T00:00:00Z",
                    published_at=published_at,
                    available_at=available_at,
                    retrieved_at=capture.retrieved_at,
                    capture_id=capture.capture_id,
                    revision_status=RevisionStatus.ORIGINAL,
                    footnotes=footnotes,
                )
                observations.append(Observation(f"obs-{series_id.lower()}-{period}", capture.source_id, series_id, period, BLSCPIAdapter.SERIES_DIMENSIONS[series_id], (version,)))
        return BLSParseResult(tuple(observations), tuple(quarantined))

    @staticmethod
    def _footnote_texts(values: object) -> list[str]:
        if not isinstance(values, list):
            return ["invalid_footnotes"]
        result: list[str] = []
        for value in values:
            if isinstance(value, dict):
                text = value.get("text") or value.get("code")
                if text:
                    result.append(str(text))
        return result

    @staticmethod
    def to_event(period: str, observations: tuple[Observation, ...], release: SourceRelease, *, evidence_ids: tuple[str, ...]) -> Event:
        selected = tuple(observation for observation in observations if observation.reference_period == period)
        if not selected:
            raise ValueError("no observations for event period")
        if release.reference_period != period:
            raise ValueError("release period does not match event period")
        available = release.available_at
        for observation in selected:
            if observation.latest.available_at:
                available = _iso_max(available or observation.latest.available_at, observation.latest.available_at)
        return Event(
            event_id=f"event-{release.source_id}-{period}",
            event_type=release.event_type,
            source_id=release.source_id,
            reference_period=period,
            occurred_at=f"{period}-01T00:00:00Z",
            effective_at=f"{period}-01T00:00:00Z",
            published_at=release.published_at,
            available_at=available,
            observation_ids=tuple(observation.observation_id for observation in selected),
            evidence_ids=evidence_ids,
        )


__all__ = ["BLSCPIAdapter", "BLSClient", "BLSHTTPError", "BLSParseResult", "BLSQuarantineError", "CapturedBLSResponse"]
