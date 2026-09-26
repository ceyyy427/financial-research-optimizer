#!/usr/bin/env python3
"""Create an immutable source snapshot and source adapter manifest from a raw file."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def create_snapshot(source_id, input_path, output_dir, request_url, request_params=None, response_status=200, content_type="application/octet-stream", parser_version="source_adapter_v1", access_method="official_download", source_authority="unknown", authorization_status="not_required", point_in_time_status="unknown", revision_status="unknown", license_name="unknown", retrieved_at=None, fallback_used=False):
    input_path = Path(input_path)
    body = input_path.read_bytes()
    snapshot_hash = hashlib.sha256(body).hexdigest()
    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    snapshot_id = f"{source_id}-{snapshot_hash[:16]}"
    source_dir = Path(output_dir) / source_id
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_file = source_dir / f"{snapshot_id}.raw"
    manifest_file = source_dir / f"{snapshot_id}.json"
    if not raw_file.exists():
        raw_file.write_bytes(body)
    manifest = {
        "snapshot_id": snapshot_id,
        "source_id": source_id,
        "request_url": request_url,
        "request_params": request_params or {},
        "retrieved_at": retrieved_at,
        "response_status": response_status,
        "content_type": content_type,
        "response_hash": f"sha256:{snapshot_hash}",
        "snapshot_hash": f"sha256:{snapshot_hash}",
        "raw_file": str(raw_file),
        "parser_version": parser_version,
        "provider_version": parser_version,
        "access_method": access_method,
        "source_authority": source_authority,
        "authorization_status": authorization_status,
        "point_in_time_status": point_in_time_status,
        "revision_status": revision_status,
        "license": license_name,
        "cache_expiry": None,
        "fallback_used": fallback_used,
    }
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/snapshots"))
    parser.add_argument("--request-url", required=True)
    parser.add_argument("--request-params", default="{}")
    parser.add_argument("--response-status", type=int, default=200)
    parser.add_argument("--content-type", default="application/octet-stream")
    parser.add_argument("--parser-version", default="source_adapter_v1")
    parser.add_argument("--access-method", default="official_download")
    parser.add_argument("--source-authority", default="unknown")
    parser.add_argument("--authorization-status", default="not_required")
    parser.add_argument("--point-in-time-status", default="unknown")
    parser.add_argument("--revision-status", default="unknown")
    parser.add_argument("--license", dest="license_name", default="unknown")
    parser.add_argument("--retrieved-at")
    parser.add_argument("--fallback-used", action="store_true")
    args = parser.parse_args()
    manifest = create_snapshot(args.source_id, args.input, args.output_dir, args.request_url, json.loads(args.request_params), args.response_status, args.content_type, args.parser_version, args.access_method, args.source_authority, args.authorization_status, args.point_in_time_status, args.revision_status, args.license_name, args.retrieved_at, args.fallback_used)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
