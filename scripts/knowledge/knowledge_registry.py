"""Load the repository's structured, citation-bound knowledge cards."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional for installed minimal runtime
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = ROOT / "knowledge"


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        return {"knowledge_id": path.stem, "title": path.stem, "summary": "知识卡片依赖 PyYAML 才能加载", "status": "not_available"}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def all_knowledge(root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = (root or KNOWLEDGE_ROOT) / "concepts"
    return {path.stem: _load_yaml(path) for path in sorted(base.glob("*.yaml"))}


def get_knowledge(knowledge_id: str, root: Path | None = None) -> dict[str, Any]:
    return dict(all_knowledge(root).get(knowledge_id, {"knowledge_id": knowledge_id, "status": "not_available"}))


def get_knowledge_for_metric(metric_id: str, root: Path | None = None) -> dict[str, Any]:
    aliases = {"forecast_rmse": "rmse", "rmse": "rmse", "mae": "mae", "cvar": "cvar", "es": "cvar", "coverage": "calibration"}
    return get_knowledge(aliases.get(str(metric_id).lower(), str(metric_id).lower()), root)


def get_knowledge_for_model(model_id: str, root: Path | None = None) -> dict[str, Any]:
    value = str(model_id).lower()
    return get_knowledge("naive_forecast" if "naive" in value else "rolling_mean" if "rolling" in value else "rolling_mean", root)


def get_knowledge_for_reason(reason: str, root: Path | None = None) -> dict[str, Any]:
    value = str(reason).lower()
    return get_knowledge("ood_detection" if "ood" in value else "calibration" if "calibr" in value else "point_in_time", root)


def validate_registry(root: Path | None = None) -> dict[str, Any]:
    cards = all_knowledge(root)
    invalid = [key for key, card in cards.items() if not card.get("knowledge_id") or not card.get("sources")]
    return {"status": "pass" if not invalid else "failed", "count": len(cards), "invalid": invalid}
