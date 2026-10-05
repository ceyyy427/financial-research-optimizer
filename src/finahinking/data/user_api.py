"""Bounded JSON connector for user-configured data APIs."""

from __future__ import annotations

import inspect
import json
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

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
    def request(self, url: str, *, headers: Mapping[str, str], timeout: float, allow_redirects: bool = False) -> TransportResponse: ...


class UserDataConnector(Protocol):
    def fetch(self, request: DataRequest) -> DataBatch: ...


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        raise DataConnectorError("target", "data source URL is invalid") from None
    return parsed.scheme.lower(), (parsed.hostname or "").lower().rstrip("."), port


def _default_resolver(host: str, port: int | None) -> tuple[str, ...]:
    try:
        rows = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
    except OSError:
        return ()
    values: list[str] = []
    for row in rows:
        sockaddr = row[4]
        if isinstance(sockaddr, tuple) and sockaddr:
            values.append(str(sockaddr[0]))
    return tuple(values)


def _forbidden_address(value: str) -> bool:
    try:
        address = ip_address(value)
    except ValueError:
        return False
    return bool(address.is_loopback or address.is_private or address.is_link_local or address.is_reserved or address.is_unspecified or address.is_multicast)


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
    def __init__(self, config: DataConnectionConfig, credential_store: DataCredentialStore, transport: DataTransport, *, resolver: Any | None = None) -> None:
        self.config = config
        self.credential_store = credential_store
        self.transport = transport
        self._resolver = resolver or _default_resolver
        self._validate_target_url(config.base_url)

    def _validate_target_url(self, url: str) -> None:
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError
            if _origin(url) != _origin(self.config.base_url):
                raise ValueError
            resolver = self._resolver
            try:
                values = resolver(parsed.hostname, parsed.port)
            except TypeError:
                values = resolver(parsed.hostname)
            for value in values or ():
                candidate = value[-1] if isinstance(value, tuple) else value
                if _forbidden_address(str(candidate)):
                    raise ValueError
        except DataConnectorError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError):
            raise DataConnectorError("target", "data source target is not allowed") from None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        try:
            if self.config.auth_mode == "bearer":
                secret = self.credential_store.resolve(self.config.credential_ref)  # type: ignore[arg-type]
                headers["Authorization"] = f"Bearer {secret}"
            elif self.config.auth_mode == "api_key_header":
                secret = self.credential_store.resolve(self.config.credential_ref)  # type: ignore[arg-type]
                headers[self.config.auth_header or "X-API-Key"] = secret
        except (KeyError, TypeError, ValueError):
            raise DataConnectorError("credential", "data credential is not configured") from None
        return headers

    def _transport_request(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        request = self.transport.request
        try:
            parameters = inspect.signature(request).parameters
            supports_flag = "allow_redirects" in parameters or any(item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters.values())
        except (TypeError, ValueError):
            supports_flag = False
        if supports_flag:
            return request(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False)
        return request(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)

    def _request(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        self._validate_target_url(url)
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._transport_request(url, headers)
            except TimeoutError:
                if attempt < MAX_RETRIES:
                    continue
                raise DataConnectorError("timeout", "data request timed out") from None
            except (OSError, RuntimeError, TypeError, ValueError, KeyError):
                if attempt < MAX_RETRIES:
                    continue
                raise DataConnectorError("transport", "data request failed") from None
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
            try:
                self._validate_target_url(final_url)
            except DataConnectorError as exc:
                if exc.code == "target":
                    raise DataConnectorError("redirect", "data source redirected to a different origin") from None
                raise
            if len(response.body) > MAX_RESPONSE_BYTES:
                raise DataConnectorError("response_too_large", "data response exceeds the size limit")
            return response
        raise DataConnectorError("transport", "data request failed") from None

    def fetch(self, request: DataRequest) -> DataBatch:
        headers = self._headers()
        records: list[Mapping[str, Any]] = []
        seen_urls: set[str] = set()
        seen_next_targets: set[str] = set()
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
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise DataConnectorError("invalid_json", "data source did not return valid JSON") from None
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
            next_url = urljoin(url, next_value)
            if next_url in seen_next_targets:
                raise DataConnectorError("pagination", "data source pagination repeated a cursor")
            seen_next_targets.add(next_url)
            try:
                self._validate_target_url(next_url)
            except DataConnectorError:
                raise DataConnectorError("redirect", "data source pagination changed origin") from None
            url = next_url
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
