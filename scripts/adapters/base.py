"""Common adapter interface and authorization boundary."""
from dataclasses import dataclass


class AdapterError(RuntimeError):
    pass


@dataclass
class AdapterContext:
    profile: dict
    authorization_status: str = "unknown"
    access_method: str | None = None


class SourceAdapter:
    source_id = "generic"

    def __init__(self, profile, authorization_status="unknown", access_method=None):
        self.context = AdapterContext(profile, authorization_status, access_method or profile.get("primary_method"))

    @property
    def profile(self):
        return self.context.profile

    def access_plan(self):
        return {
            "source_id": self.profile["source_id"],
            "access_method": self.context.access_method,
            "fallback_methods": self.profile.get("fallback_methods", []),
            "authorization_status": self.context.authorization_status,
            "point_in_time": self.profile.get("point_in_time", False),
            "revision_aware": self.profile.get("revision_aware", False),
        }

    def require_authorization(self):
        required = self.profile.get("authentication", {}).get("required") or self.profile.get("access_policy") in {"licensed_only", "authorized_only"}
        if required and self.context.authorization_status != "authorized":
            raise AdapterError(f"{self.profile['source_id']} requires authorized access; status={self.context.authorization_status}")

    def fetch(self, *args, **kwargs):
        raise AdapterError(f"{self.profile['source_id']} has no generic fetch implementation; use its declared API/browser/upload adapter")
