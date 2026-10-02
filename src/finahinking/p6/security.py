"""Prompt and payload boundary checks for the P6 agent surface."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

_FORBIDDEN = (
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"\b(?:shell|bash|zsh|powershell)\s+(?:command|script)", re.IGNORECASE),
    re.compile(r"\b(?:pip|conda|uv)\s+install\b", re.IGNORECASE),
    re.compile(r"\b(?:rewrite|alter|change)\s+(?:the\s+)?provenance\b", re.IGNORECASE),
    re.compile(r"\bdelete\s+(?:the\s+)?(?:artifact|record|run)\b", re.IGNORECASE),
    re.compile(r"\b(?:subprocess|os\.system|source_code|generated_python|generated_shell)\b", re.IGNORECASE),
    re.compile(r"\bimport\s+[A-Za-z_][\w.]*|\bfrom\s+[A-Za-z_][\w.]*\s+import\b", re.IGNORECASE),
    re.compile(r"\b(?:python|python3|bash|sh|zsh)\s+-c\b", re.IGNORECASE),
    re.compile(r"\b(?:ignore|disregard|bypass)\s+(?:all\s+)?(?:previous|prior|system|safety|policy)\b", re.IGNORECASE),
    re.compile(r"\b(?:modify|edit|rewrite|delete|erase)\s+(?:the\s+)?(?:source|record|run|artifact|provenance)\b", re.IGNORECASE),
    re.compile(r"\b(?:invoke|call|use)\s+(?:an?\s+)?(?:raw|unapproved|private)\s+(?:adapter|library|tool)\b", re.IGNORECASE),
    re.compile(r"\b(?:curl|wget|http://|https://|file://)\b", re.IGNORECASE),
)
_FORBIDDEN_KEYS = {
    "__class__", "__code__", "__globals__", "__import__", "callable", "import", "imports", "module", "path", "file_path", "url", "uri", "source", "source_code",
    "generated_python", "generated_shell", "command", "subprocess", "delete", "delete_artifact",
    "rewrite_provenance", "package_install", "eval", "exec", "adapter", "adapter_name",
}
_ARBITRARY_LOCATION = re.compile(r"(?:^[~/]|^\.\.?/|^[A-Za-z]:[\\/]|^[A-Za-z][A-Za-z0-9+.-]*://)")


def validate_agent_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("agent text is required")
    if any(pattern.search(text) for pattern in _FORBIDDEN):
        raise ValueError("agent text contains a forbidden execution or mutation directive")
    return text


def validate_untrusted_text(text: str) -> str:
    return validate_agent_text(text)


def validate_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("payload keys must be text")
            if key.casefold().replace("-", "_") in _FORBIDDEN_KEYS:
                raise ValueError("payload contains a forbidden key")
            validate_agent_text(key)
            validate_payload(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_payload(item)
    elif isinstance(value, str):
        validate_agent_text(value)
        if _ARBITRARY_LOCATION.search(value):
            raise ValueError("payload contains an arbitrary location")
    elif isinstance(value, (bytes, bytearray, set, frozenset)):
        raise TypeError("payload must contain bounded JSON values")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("payload contains a non-finite number")
    elif not isinstance(value, (int, float, bool, type(None))):
        raise TypeError("payload must contain bounded JSON values")
    return value


__all__ = ["validate_agent_text", "validate_payload", "validate_untrusted_text"]
