"""CDP/network event records with secret-safe headers and optional bodies."""
import hashlib
import json
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone
from pathlib import Path


SENSITIVE = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"}


def redact_headers(headers):
    return {key: ("[REDACTED]" if key.lower() in SENSITIVE else value) for key, value in (headers or {}).items()}


class NetworkClassifier:
    """Classify network records so data APIs are not mixed with page noise."""

    TRACKING_TOKENS = ("analytics", "collect", "pixel", "telemetry", "beacon", "doubleclick")
    AUTH_TOKENS = ("login", "oauth", "authorize", "token", "captcha", "signin")
    DATA_TOKENS = ("api", "query", "data", "series", "observations", "quote", "market", "sdmx", "xbrl", "filing")
    STATIC_EXTENSIONS = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2", ".ico")

    @classmethod
    def classify(cls, url, method="GET", status=0, request_headers=None, response_headers=None, body=b""):
        parsed = urlparse(url or "")
        lower = (url or "").lower()
        content_type = ""
        for key, value in (response_headers or {}).items():
            if key.lower() == "content-type":
                content_type = str(value).lower()
                break
        query = parse_qs(parsed.query)
        pagination = any(key.lower() in {"page", "page_size", "offset", "limit", "cursor", "start", "from", "to"} for key in query)
        if any(token in lower for token in cls.TRACKING_TOKENS):
            classification, confidence = "tracking_request", 0.98
        elif any(token in lower for token in cls.AUTH_TOKENS):
            classification, confidence = "auth_request", 0.92
        elif parsed.path.lower().endswith(cls.STATIC_EXTENSIONS):
            classification, confidence = "static_asset", 0.98
        elif "json" in content_type or "csv" in content_type or any(token in lower for token in cls.DATA_TOKENS):
            classification, confidence = "financial_data_api", 0.94 if "api" in lower or "json" in content_type else 0.78
        else:
            classification, confidence = "unknown", 0.45
        schema = None
        if "json" in content_type and body:
            try:
                payload = json.loads(body.decode("utf-8"))
                schema = {"type": type(payload).__name__, "keys": sorted(payload)[:32] if isinstance(payload, dict) else []}
            except (UnicodeDecodeError, json.JSONDecodeError):
                schema = {"type": "invalid_json"}
        return {
            "request_type": classification,
            "classification": classification,
            "confidence": confidence,
            "data_endpoint": classification == "financial_data_api",
            "pagination": pagination,
            "response_schema": schema,
            "is_data_request": classification == "financial_data_api",
            "is_tracking_request": classification == "tracking_request",
            "is_auth_request": classification == "auth_request",
            "is_static_asset": classification == "static_asset",
            "http_status": status,
        }


class NetworkRecorder:
    def __init__(self, source_id, capture_bodies=False, raw_body_dir=None, max_body_bytes=25_000_000):
        self.source_id = source_id
        self.capture_bodies = capture_bodies
        self.raw_body_dir = Path(raw_body_dir) if raw_body_dir else None
        self.max_body_bytes = max_body_bytes
        self.records = []

    def record_response(self, request_id, url, method, status, request_headers=None, response_headers=None, body=None, page_url=""):
        body_bytes = body if isinstance(body, bytes) else str(body or "").encode("utf-8")
        record = {
            "request_id": request_id,
            "url": url,
            "method": method,
            "status": status,
            "request_headers_hash": hashlib.sha256(json.dumps(redact_headers(request_headers), sort_keys=True).encode()).hexdigest(),
            "response_headers_hash": hashlib.sha256(json.dumps(redact_headers(response_headers), sort_keys=True).encode()).hexdigest(),
            "content_type": (response_headers or {}).get("content-type", ""),
            "body_hash": hashlib.sha256(body_bytes).hexdigest(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "page_url": page_url,
            "source_id": self.source_id,
        }
        record["body_size"] = len(body_bytes)
        record.update(NetworkClassifier.classify(url, method, status, request_headers, response_headers, body_bytes))
        if self.capture_bodies and self.raw_body_dir and len(body_bytes) <= self.max_body_bytes:
            self.raw_body_dir.mkdir(parents=True, exist_ok=True)
            body_file = self.raw_body_dir / f"{hashlib.sha256((self.source_id + ':' + request_id).encode()).hexdigest()[:24]}.body"
            if not body_file.exists():
                body_file.write_bytes(body_bytes)
            record["body_file"] = str(body_file)
        elif self.capture_bodies and len(body_bytes) > self.max_body_bytes:
            record["body_capture_status"] = "skipped_size_limit"
        elif self.capture_bodies:
            record["body_capture_status"] = "hash_only_no_raw_body_dir"
        self.records.append(record)
        return record

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"source_id": self.source_id, "capture_bodies": self.capture_bodies, "records": self.records}, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
