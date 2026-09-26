"""Save a page snapshot without treating rendered text as canonical data."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


async def save_page_snapshot(page, root, source_id, include_screenshot=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    html_text = await page.content()
    digest = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    raw_file = root / f"{source_id}-{digest[:16]}.html"
    raw_file.write_text(html_text, encoding="utf-8")
    manifest = {"source_id": source_id, "page_url": getattr(page, "url", ""), "retrieved_at": datetime.now(timezone.utc).isoformat(), "raw_file": str(raw_file), "snapshot_hash": digest}
    if include_screenshot:
        screenshot = root / f"{source_id}-{digest[:16]}.png"
        await page.screenshot(path=str(screenshot), full_page=True)
        manifest["screenshot_file"] = str(screenshot)
    metadata = raw_file.with_suffix(".json")
    metadata.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
