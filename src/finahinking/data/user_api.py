"""Bounded JSON connector for user-configured data APIs."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .connection_settings import DataCredentialStore
from .field_mapping import normalize_records
from .user_api_contracts import DataBatch, DataConnectionConfig, DataRequest

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 10_000
MAX_PAGES = 20
REQUEST_TIMEOUT_SECONDS = 15.0
MAX_RETRIES = 2


class DataConnectorError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    url: str | None = None


class DataTransport(Protocol):
    def request(self, url: str, *, headers: Mapping[str, str], timeout: float) -> TransportResponse: ...


class UserDataConnector(Protocol):
    def fetch(self, request: DataRequest) -> DataBatch: ...


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    port = parsed.port
    return parsed.scheme.lower(), (parsed.hostname or "").lower().rstrip("."), port


def _append_query(url: str, request: DataRequest, page: int) -> str:
    parsed = urlsplit(url)
    values = list(parse_qsl(parsed.query, keep_blank_values=False))
    values.extend([("dataset_kind", request.dataset_kind), ("page", str(page))])
    if request.instruments:
        values.append(("instruments", ",".join(request.instruments)))
    if request.start:
        values.append(("start", request.start))
    if request.end:
        values.append(("end", request.end))
    if request.as_of:
        values.append(("as_of", request.as_of))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(values), ""))


def _path_value(payload: object, path: str | None) -> object:
    if path is None:
        return payload
    value = payload
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise DataConnectorError("schema", "data response records path is missing")
        value = value[part]
    return value


class JsonApiConnector:
    def __init__(self, config: DataConnectionConfig, credential_store: DataCredentialStore, transport: DataTransport) -> None:
        self.config = config
        self.credential_store = credential_store
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        try:
            if self.config.auth_mode == "bearer":
                secret = self.credential_store.resolve(self.config.credential_ref)  # type: ignore[arg-type]
                headers["Authorization"] = f"Bearer {secret}"
            elif self.config.auth_mode == "api_key_header":
                secret = self.credential_store.resolve(self.config.credential_ref)  # type: ignore[arg-type]
                headers[self.config.auth_header or "X-API-Key"] = secret
        except Exception as exc:
            raise DataConnectorError("credential", "data credential is not configured") from exc
        return headers

    def _request(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        last: BaseException | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.transport.request(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            except TimeoutError as exc:
                last = exc
                if attempt < MAX_RETRIES:
                    continue
                raise DataConnectorError("timeout", "data request timed out") from exc
            except Exception as exc:
                last = exc
                if attempt < MAX_RETRIES:
                    continue
                raise DataConnectorError("transport", "data request failed") from exc
            if not isinstance(response, TransportResponse):
                raise DataConnectorError("transport", "data transport returned an invalid response")
            if not isinstance(response.body, bytes):
                raise DataConnectorError("transport", "data transport returned an invalid body")
            if (response.status_code in {408, 425, 429} or 500 <= response.status_code <= 599) and attempt < MAX_RETRIES:
                continue
            if response.status_code in {401, 403}:
                raise DataConnectorError("unauthorized", "data source rejected authentication")
            if response.status_code == 429:
                raise DataConnectorError("rate_limited", "data source rate limit reached")
            if response.status_code < 200 or response.status_code >= 300:
                raise DataConnectorError("http", "data source returned an error")
            final_url = response.url or url
            if _origin(final_url) != _origin(self.config.base_url):
                raise DataConnectorError("redirect", "data source redirected to a different origin")
            if len(response.body) > MAX_RESPONSE_BYTES:
                raise DataConnectorError("response_too_large", "data response exceeds the size limit")
            return response
        raise DataConnectorError("transport", "data request failed") from last

    def fetch(self, request: DataRequest) -> DataBatch:
        headers = self._headers()
        records: list[Mapping[str, Any]] = []
        seen_urls: set[str] = set()
        url = self.config.base_url
        for page in range(1, MAX_PAGES + 1):
            request_url = _append_query(url, request, page)
            if request_url in seen_urls:
                raise DataConnectorError("pagination", "data source pagination repeated a page")
            seen_urls.add(request_url)
            response = self._request(request_url, headers)
            content_type = next((value for key, value in response.headers.items() if key.lower() == "content-type"), "")
            if content_type and "json" not in content_type.lower():
                raise DataConnectorError("invalid_json", "data source did not return JSON")
            try:
                payload = json.loads(response.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DataConnectorError("invalid_json", "data source did not return valid JSON") from exc
            page_records = _path_value(payload, self.config.records_path)
            if not isinstance(page_records, Sequence) or isinstance(page_records, (str, bytes)) or any(not isinstance(item, Mapping) for item in page_records):
                raise DataConnectorError("schema", "data response records must be an array of objects")
            records.extend(page_records)
            if len(records) > MAX_RECORDS:
                raise DataConnectorError("record_limit", "data response exceeds the record limit")
            next_value = payload.get("next") if isinstance(payload, Mapping) else None
            if next_value in (None, "", False):
                break
            if not isinstance(next_value, str) or len(next_value) > 2048:
                raise DataConnectorError("pagination", "data response pagination cursor is invalid")
            if next_value.startswith("http"):
                if _origin(next_value) != _origin(self.config.base_url):
                    raise DataConnectorError("redirect", "data source pagination changed origin")
                url = next_value
            else:
                url = urlunsplit((*urlsplit(self.config.base_url)[:2], next_value.lstrip("/"), "", ""))
        else:
            raise DataConnectorError("pagination", "data source exceeded the page limit")
        return normalize_records(
            records,
            self.config.field_mapping,
            request.dataset_kind,
            connection_id=self.config.connection_id,
            source_declaration=self.config.source_declaration,
            retrieved_at=datetime.now(UTC),
        )


__all__ = [
    "MAX_PAGES",
    "MAX_RECORDS",
    "MAX_RESPONSE_BYTES",
    "REQUEST_TIMEOUT_SECONDS",
    "DataConnectorError",
    "DataTransport",
    "JsonApiConnector",
    "TransportResponse",
    "UserDataConnector",
]
