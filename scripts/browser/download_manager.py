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
    if target.exists():
        stem, suffix = target.stem, target.suffix
        index = 1
        while target.exists():
            target = root / f"{stem}-{index}{suffix}"
            index += 1
    await download.save_as(str(target))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"source_id": source_id, "filename": suggested, "raw_file": str(target), "sha256": digest, "saved_at": datetime.now(timezone.utc).isoformat()}
    manifest_path = target.with_suffix(target.suffix + ".json")
    temporary_manifest = manifest_path.with_name(manifest_path.name + ".tmp")
    temporary_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    return manifest
