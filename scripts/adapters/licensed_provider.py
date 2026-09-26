"""Authorized-only adapter for Wind, CSMAR, Nasdaq Data Link, and JoinQuant."""
from .base import SourceAdapter


class LicensedProviderAdapter(SourceAdapter):
    def import_snapshot(self, path):
        self.require_authorization()
        return {
            "source_id": self.profile["source_id"],
            "input_type": "user_or_authorized_snapshot",
            "path": str(path),
            "authorization_status": self.context.authorization_status,
            "parser": self.profile.get("parser"),
            "normalizer": self.profile.get("normalizer"),
        }
