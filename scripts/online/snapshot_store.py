"""Immutable raw-response snapshots and provenance manifests."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class SnapshotStore:
    def __init__(self, root):
        self.root = Path(root)

    def save(self, provider, response, provider_version, license_name, revision_policy, request_params=None):
        snapshot_hash = hashlib.sha256(response.body).hexdigest()
        snapshot_id = f"{provider}-{snapshot_hash[:16]}"
        provider_dir = self.root / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        raw_path = provider_dir / f"{snapshot_id}.raw"
        manifest_path = provider_dir / f"{snapshot_id}.json"
        if not raw_path.exists():
            raw_path.write_bytes(response.body)
        manifest = {
            "snapshot_id": snapshot_id,
            "provider": provider,
            "provider_version": provider_version,
            "request_url": response.request_url,
            "request_params": request_params if request_params is not None else response.request_params,
            "retrieved_at": response.retrieved_at,
            "http_status": response.status,
            "response_hash": response.response_hash,
            "snapshot_hash": snapshot_hash,
            "raw_file": str(raw_path),
            "cache_expiry": response.cache_expiry,
            "license": license_name,
            "revision_policy": revision_policy,
            "from_cache": response.from_cache,
            "stale": response.stale,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
