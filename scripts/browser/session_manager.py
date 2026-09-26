"""Isolated browser context paths and authorization boundaries."""
from pathlib import Path


CONTEXTS = {"anonymous_context", "authorized_context", "research_context"}


def context_path(root, context_name):
    if context_name not in CONTEXTS:
        raise ValueError(f"unknown browser context: {context_name}")
    path = Path(root) / context_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_context_request(context_name, authorized=False):
    if context_name == "authorized_context" and not authorized:
        raise PermissionError("authorized_context requires explicit user authorization")
    return {"context_name": context_name, "persistent_state_allowed": context_name == "authorized_context" and authorized, "sensitive_storage": context_name == "authorized_context"}
