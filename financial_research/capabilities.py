"""Public capability discovery without exposing internal handler registries."""
from pathlib import Path


def get_capabilities(registry_path="config/source_registry.yaml"):
    try:
        from scripts.adapters.status import adapter_status
        report = adapter_status(Path(registry_path))
        return {"schema_version": "1.0", "status": "ready", "maturity": report, "source_count": len(report.get("profiles", []))}
    except Exception as exc:
        return {"schema_version": "1.0", "status": "degraded", "reason_code": "CAPABILITY_REGISTRY_UNAVAILABLE", "error": str(exc)}
