#!/usr/bin/env python3
"""Build a refresh plan; never retrains a model merely because data arrived."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .config_utils import load_config
except ImportError:
    from config_utils import load_config


DEFAULT_POLICY = {"prices": "intraday", "macro_data": "on_release", "features": "daily", "forecast": "daily", "retrain": "weekly", "full_research": "monthly"}


def build_refresh_plan(config, now=None):
    policy = {**DEFAULT_POLICY, **config.get("refresh_policy", {})}
    now = now or datetime.now(timezone.utc).isoformat()
    return {"generated_at": now, "mode": config["mode"], "policy": policy, "stages": [
        {"stage": "data_refresh", "cadence": policy["prices"], "trigger": "new price/provider observation", "action": "update_snapshot_only"},
        {"stage": "feature_refresh", "cadence": policy["features"], "trigger": "data snapshot changed", "action": "recompute_features_without_retraining"},
        {"stage": "forecast_refresh", "cadence": policy["forecast"], "trigger": "available feature snapshot changed", "action": "forecast_with_frozen_model"},
        {"stage": "model_retrain", "cadence": policy["retrain"], "trigger": "scheduled cadence or drift threshold", "action": "retrain_only_after_validation"},
        {"stage": "full_research", "cadence": policy["full_research"], "trigger": "major revision, monthly audit, or contract change", "action": "rerun_preflight_and_full_audit"},
    ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_refresh_plan(load_config(args.config))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
