from __future__ import annotations

import json

import pytest

from finahinking.research.provider_status import provider_status_payload
from finahinking.research.providers import load_provider_config_from_mapping


def _config() -> dict[str, object]:
    return {
        "defaults": {"provider": "offline", "model": "fixture-v1", "role_models": {"factor": "fixture-v1"}},
        "providers": [
            {"name": "offline", "model": "fixture-v1", "capabilities": ["structured_output", "offline"], "enabled": True, "offline": True},
            {"name": "user-compatible", "model": "user-model", "capabilities": ["structured_output"], "enabled": True, "offline": False, "credential_ref": {"env_var": "FINAHINK_USER_API_KEY"}},
        ],
    }


def test_status_reports_readiness_without_exposing_secret_value() -> None:
    secret = "user-secret-value"
    payload = provider_status_payload(_config(), {"FINAHINK_USER_API_KEY": secret})
    encoded = json.dumps(payload, ensure_ascii=False)
    user = next(item for item in payload["providers"] if item["provider"] == "user-compatible")

    assert user["configured"] is True
    assert user["credential_ref"] == {"env_var": "FINAHINK_USER_API_KEY"}
    assert secret not in encoded
    assert "role_models" in payload


def test_status_distinguishes_missing_reference_and_offline_provider() -> None:
    payload = provider_status_payload(_config(), {})
    offline = next(item for item in payload["providers"] if item["provider"] == "offline")
    user = next(item for item in payload["providers"] if item["provider"] == "user-compatible")

    assert offline["configured"] is True
    assert user["configured"] is False
    assert user["reason"] == "credential is not configured"


def test_provider_config_rejects_raw_secret_fields_and_invalid_env_names() -> None:
    with pytest.raises(ValueError, match="secret"):
        load_provider_config_from_mapping({**_config(), "providers": [{"name": "bad", "api_key": "raw-secret"}]})
    with pytest.raises(ValueError, match="environment"):
        provider_status_payload({**_config(), "providers": [{"name": "bad", "credential_ref": {"env_var": "not-safe"}}]}, {})

