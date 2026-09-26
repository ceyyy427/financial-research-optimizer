"""CDP/network event records with secret-safe headers and optional bodies."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SENSITIVE = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"}


def redact_headers(headers):
    return {key: ("[REDACTED]" if key.lower() in SENSITIVE else value) for key, value in (headers or {}).items()}


class NetworkRecorder:
    def __init__(self, source_id, capture_bodies=False):
        self.source_id = source_id
        self.capture_bodies = capture_bodies
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
        if self.capture_bodies:
            record["body"] = body_bytes.decode("utf-8", errors="replace")
        self.records.append(record)
        return record

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"source_id": self.source_id, "capture_bodies": self.capture_bodies, "records": self.records}, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
