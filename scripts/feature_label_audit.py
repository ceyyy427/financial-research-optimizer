#!/usr/bin/env python3
"""Audit feature availability and label overlap at a time-series split boundary."""
from datetime import timedelta

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - exercised in dependency-free environments
    raise SystemExit("feature_label_audit.py requires pandas; install with python3 -m pip install -e '.[test]'") from exc


def _timestamp(value):
    return pd.to_datetime(value, errors="coerce", utc=True)


def validate_contract(contract):
    errors = []
    for section in ("features", "labels"):
        for index, item in enumerate(contract.get(section, [])):
            if not isinstance(item, dict):
                errors.append(f"{section}[{index}] must be an object")
                continue
            fields = ("feature_id", "formula", "source_ids", "observation_time", "availability_time", "forecast_origin", "label_horizon", "purge_required", "embargo_required", "point_in_time_safe", "lineage") if section == "features" else ("label_id", "formula", "source_ids", "observation_time", "availability_time", "forecast_origin", "label_horizon", "purge_required", "embargo_required", "point_in_time_safe", "label_start", "label_end", "overlap_group", "lineage")
            missing = [field for field in fields if field not in item]
            if missing:
                errors.append(f"{section}[{index}] missing {missing}")
            if item.get("point_in_time_safe") is not True:
                errors.append(f"{section}[{index}] is not marked point_in_time_safe")
    return errors


def calculate_purge_gap(label_horizon, frequency="daily"):
    digits = "".join(character for character in str(label_horizon) if character.isdigit())
    horizon = int(digits or 0)
    return horizon if frequency == "daily" else max(1, horizon)


def audit_availability(frame, availability_field, forecast_origin):
    origin = _timestamp(forecast_origin)
    values = _timestamp(frame[availability_field]) if availability_field in frame else pd.Series(dtype="datetime64[ns, UTC]")
    future = int((values > origin).sum()) if not values.empty else 0
    invalid = int(values.isna().sum()) if not values.empty else 0
    return {"availability_field": availability_field, "future_rows": future, "invalid_rows": invalid, "point_in_time_safe": future == 0 and invalid == 0}


def audit_label_split(train_labels, evaluation_labels, purge_period=0, embargo_period=0):
    """Check that train labels do not cross into the evaluation information set."""
    train = train_labels.copy()
    evaluation = evaluation_labels.copy()
    for frame in (train, evaluation):
        frame["label_start"] = _timestamp(frame["label_start"])
        frame["label_end"] = _timestamp(frame["label_end"])
    if train.empty or evaluation.empty:
        return {"overlap_rows": 0, "purge_period": purge_period, "embargo_period": embargo_period, "safe": True}
    train_end = train["label_end"].max()
    evaluation_start = evaluation["label_start"].min()
    boundary = train_end + timedelta(days=int(purge_period) + int(embargo_period))
    overlap_rows = int((evaluation["label_start"] <= boundary).sum())
    return {"overlap_rows": overlap_rows, "purge_period": purge_period, "embargo_period": embargo_period, "safe": overlap_rows == 0}


def audit_feature_label_contract(frame, contract, forecast_origin, train_labels=None, evaluation_labels=None):
    contract_errors = validate_contract(contract)
    availability = audit_availability(frame, contract["availability_time_field"], forecast_origin)
    label_horizons = [item.get("label_horizon") for item in contract.get("labels", [])]
    result = {"availability": availability, "lineage_fields": len(contract.get("features", [])) + len(contract.get("labels", [])), "contract_errors": contract_errors, "computed_purge_gap": max((calculate_purge_gap(value) for value in label_horizons), default=0)}
    if train_labels is not None and evaluation_labels is not None:
        result["label_split"] = audit_label_split(train_labels, evaluation_labels, contract.get("purge_period", 0), contract.get("embargo_period", 0))
    result["safe"] = not contract_errors and availability["point_in_time_safe"] and result.get("label_split", {}).get("safe", True)
    return result
