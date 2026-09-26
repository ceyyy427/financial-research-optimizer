"""File cache and HTTP transport with raw-response preservation.

The transport is injectable so provider tests never need an internet connection.
"""
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .retry_policy import RetryPolicy


class HttpRequestError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


@dataclass
class CachedResponse:
    status: int
    headers: dict
    body: bytes
    request_url: str
    request_params: dict
    retrieved_at: str
    cache_expiry: str
    response_hash: str
    raw_file: str
    from_cache: bool = False
    stale: bool = False


SENSITIVE_KEYS = {"api_key", "apikey", "token", "access_token", "authorization", "password", "secret"}


def _redact_params(params):
    return {key: ("[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else value) for key, value in (params or {}).items()}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_request(method, url, params, headers):
    material = json.dumps({"method": method, "url": url, "params": _redact_params(params), "headers": _redact_params(headers)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _url_with_params(url, params):
    if not params:
        return url
    parsed = urlsplit(url)
    query = urlencode(sorted(params.items()), doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))


def _redact_url(url):
    parsed = urlsplit(url)
    query = []
    for item in parsed.query.split("&") if parsed.query else []:
        key = item.split("=", 1)[0]
        query.append(f"{key}=%5BREDACTED%5D" if key.lower() in SENSITIVE_KEYS else item)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "&".join(query), parsed.fragment))


class HttpCache:
    def __init__(self, root, transport=None, retry_policy=None, clock=None):
        self.root = Path(root)
        self.transport = transport
        self.retry_policy = retry_policy or RetryPolicy()
        self.clock = clock or time.time

    def _paths(self, key):
        return self.root / f"{key}.body", self.root / f"{key}.json"

    def _load(self, key):
        body_path, meta_path = self._paths(key)
        if not body_path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        body = body_path.read_bytes()
        return CachedResponse(body=body, from_cache=True, stale=False, **meta)

    def _write(self, key, response):
        self.root.mkdir(parents=True, exist_ok=True)
        body_path, meta_path = self._paths(key)
        body_path.write_bytes(response.body)
        payload = {
            "status": response.status,
            "headers": response.headers,
            "request_url": response.request_url,
            "request_params": response.request_params,
            "retrieved_at": response.retrieved_at,
            "cache_expiry": response.cache_expiry,
            "response_hash": response.response_hash,
            "raw_file": str(body_path),
        }
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _network(self, method, url, params, headers, timeout):
        request_url = _url_with_params(url, params)
        if self.transport:
            status, response_headers, body = self.transport(method, request_url, headers or {}, timeout)
            return status, dict(response_headers or {}), body if isinstance(body, bytes) else str(body).encode("utf-8"), request_url
        request = Request(request_url, headers=headers or {}, method=method.upper())
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.status, dict(response.headers.items()), response.read(), request_url
        except HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            raise HttpRequestError(f"HTTP {exc.code} for {request_url}: {body[:200]!r}", status=exc.code) from exc
        except URLError as exc:
            raise HttpRequestError(f"network error for {request_url}: {exc.reason}") from exc

    def request(self, method, url, params=None, headers=None, ttl_seconds=86400, timeout=30, allow_stale=True):
        params = dict(params or {})
        headers = dict(headers or {})
        key = _hash_request(method.upper(), url, params, headers)
        cached = self._load(key)
        if cached:
            try:
                fresh = self.clock() < float(cached.cache_expiry)
            except (TypeError, ValueError):
                fresh = False
            if fresh:
                return cached

        def operation():
            status, response_headers, body, request_url = self._network(method, url, params, headers, timeout)
            if status >= 400:
                raise HttpRequestError(f"HTTP {status} for {request_url}", status=status)
            now = self.clock()
            return CachedResponse(
                status=status,
                headers=response_headers,
                body=body,
                request_url=_redact_url(request_url),
                request_params=_redact_params(params),
                retrieved_at=_now(),
                cache_expiry=str(now + max(0, ttl_seconds)),
                response_hash=hashlib.sha256(body).hexdigest(),
                raw_file="",
            )

        try:
            response = self.retry_policy.run(operation)
            response.raw_file = str(self._paths(key)[0])
            self._write(key, response)
            return response
        except Exception:
            if cached and allow_stale:
                cached.stale = True
                return cached
            raise
