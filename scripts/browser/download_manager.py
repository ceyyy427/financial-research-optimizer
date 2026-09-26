"""Persist browser downloads as hashed raw artifacts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


async def save_download(download, root, source_id):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    suggested = getattr(download, "suggested_filename", "download.bin")
    target = root / suggested
    await download.save_as(str(target))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"source_id": source_id, "filename": suggested, "raw_file": str(target), "sha256": digest, "saved_at": datetime.now(timezone.utc).isoformat()}
    manifest_path = target.with_suffix(target.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
