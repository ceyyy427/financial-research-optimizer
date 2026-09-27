"""Explicit, opt-in authorized-context checkpointing.

Cookie/local-storage values are written only to a private 0600 state file.
The manifest is safe to commit and contains counts and hashes, never values.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


async def save_auth_checkpoint(context, path, allow_persist=False):
    if not allow_persist:
        raise PermissionError("auth checkpoint persistence requires explicit opt-in")
    manifest_target = Path(path)
    state_target = manifest_target.with_name("auth_state.private.json")
    state = await context.storage_state()
    state_target.parent.mkdir(parents=True, exist_ok=True)
    state_target.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    state_target.chmod(0o600)
    state_hash = hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    safe_state = {
        "checkpoint_version": "1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "origins": [item.get("origin") for item in state.get("origins", [])],
        "cookie_count": len(state.get("cookies", [])),
        "cookie_hash": hashlib.sha256(json.dumps(state.get("cookies", []), sort_keys=True).encode()).hexdigest(),
        "state_hash": state_hash,
        "private_state_file": str(state_target),
        "sensitive_values_persisted": True,
    }
    manifest_target.write_text(json.dumps(safe_state, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_target.chmod(0o600)
    return {"path": str(manifest_target), "private_state_path": str(state_target), "cookie_count": safe_state["cookie_count"], "cookie_hash": safe_state["cookie_hash"], "state_hash": state_hash, "sensitive_values_persisted": True}
