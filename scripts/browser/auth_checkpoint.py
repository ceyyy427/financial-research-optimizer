"""Explicit, opt-in authorized-context checkpointing."""
import hashlib
import json
from pathlib import Path


async def save_auth_checkpoint(context, path, allow_persist=False):
    if not allow_persist:
        raise PermissionError("auth checkpoint persistence requires explicit opt-in")
    state = await context.storage_state()
    safe_state = {
        "origins": [{"origin": item.get("origin"), "localStorage": []} for item in state.get("origins", [])],
        "cookie_count": len(state.get("cookies", [])),
        "cookie_hash": hashlib.sha256(json.dumps(state.get("cookies", []), sort_keys=True).encode()).hexdigest(),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(safe_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(target), "cookie_count": safe_state["cookie_count"], "cookie_hash": safe_state["cookie_hash"], "sensitive_values_persisted": False}
