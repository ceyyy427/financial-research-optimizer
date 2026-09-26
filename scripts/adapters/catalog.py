"""Official web, exchange, disclosure, and secondary catalog adapters.

These adapters deliberately expose an access plan instead of pretending that a
site-specific browser session has been authorized. Network work is delegated to
the Patchright/CDP layer and the resulting raw response must pass snapshot and
canonicalization boundaries before analysis.
"""
from .base import AdapterError, SourceAdapter


class CatalogSourceAdapter(SourceAdapter):
    def planned_request(self, topic=None, identifier=None):
        if self.profile.get("access_policy") in {"licensed_only", "authorized_only"}:
            self.require_authorization()
        return {
            **self.access_plan(),
            "topic": topic,
            "identifier": identifier,
            "base_urls": self.profile.get("base_urls", []),
            "parser": self.profile.get("parser"),
            "normalizer": self.profile.get("normalizer"),
            "quality_checks": self.profile.get("quality_checks", []),
            "browser_policy": "Patchright isolated context → CDP capture → DOM only as last fallback",
        }


def adapter_for_profile(profile, authorization_status="unknown", access_method=None):
    return CatalogSourceAdapter(profile, authorization_status, access_method)
