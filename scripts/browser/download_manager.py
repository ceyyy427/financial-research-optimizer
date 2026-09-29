"""Persist browser downloads as hashed raw artifacts."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


async def save_download(download, root, source_id, allowed_extensions=None, max_bytes=50_000_000):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    suggested = Path(getattr(download, "suggested_filename", "download.bin")).name
    if not re.fullmatch(r"[A-Za-z0-9._-]+", suggested):
        raise ValueError("unsafe download filename")
    allowed = set(allowed_extensions or {".csv", ".json", ".txt", ".xlsx", ".xls", ".pdf", ".zip"})
    if Path(suggested).suffix.lower() not in allowed:
        raise ValueError(f"download extension is not allowed: {suggested}")
    target = root / suggested
    await download.save_as(str(target))
    if target.stat().st_size > max_bytes:
        target.unlink(missing_ok=True)
        raise ValueError("download exceeds configured size limit")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"source_id": source_id, "filename": suggested, "raw_file": str(target), "sha256": digest, "saved_at": datetime.now(timezone.utc).isoformat()}
    manifest_path = target.with_suffix(target.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
