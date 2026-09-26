"""Dynamic freshness and degraded-cache status evaluation."""
from datetime import datetime, timezone


def _dt(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def check_freshness(snapshot, now=None, max_age_minutes=1440, expected_release_at=None, duplicate_ratio=0.0, provider_changed=False):
    now = _dt(now) if now else datetime.now(timezone.utc)
    if not snapshot:
        return {"status": "blocked", "reason": "no snapshot manifest", "latency_minutes": None, "cache_status": "missing"}
    retrieved = _dt(snapshot.get("retrieved_at"))
    latency = max(0.0, (now - retrieved).total_seconds() / 60.0)
    reasons = []
    status = "ready"
    if snapshot.get("stale"):
        status = "fallback"
        reasons.append("network failed and stale cache was used")
    if latency > max_age_minutes:
        status = "stale" if status == "ready" else status
        reasons.append(f"latency {latency:.1f}m exceeds {max_age_minutes}m")
    if expected_release_at and now >= _dt(expected_release_at) and snapshot.get("retrieved_at") < expected_release_at:
        status = "degraded" if status in {"ready", "stale"} else status
        reasons.append("expected release has not been observed")
    if duplicate_ratio > 0:
        status = "degraded" if status == "ready" else status
        reasons.append("duplicate rows detected")
    if provider_changed:
        status = "degraded" if status in {"ready", "stale"} else status
        reasons.append("provider changed from the previous snapshot")
    if snapshot.get("http_status", 0) >= 400:
        status = "blocked"
        reasons.append("provider returned an error status")
    return {"status": status, "reason": "; ".join(reasons) or "freshness checks passed", "latency_minutes": round(latency, 3), "cache_status": "stale" if snapshot.get("stale") else ("hit" if snapshot.get("from_cache") else "miss"), "retrieved_at": snapshot.get("retrieved_at"), "provider": snapshot.get("provider")}
