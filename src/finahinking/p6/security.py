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
    re.compile(r"\b(?:drop|alter|truncate|delete|insert|update)\s+(?:table|schema|from|into|database)\b", re.IGNORECASE),
    re.compile(r"(?:\{\{|\}\}|\{%|%\})"),
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
    """Validate bounded JSON-like data at an agent boundary.

    The limits are deliberately conservative: they prevent deep/large payloads
    from becoming an accidental execution or denial-of-service surface while
    still allowing the bounded P6 panel requests.
    """

    counters = {"nodes": 0}

    def _walk(item: Any, depth: int) -> None:
        counters["nodes"] += 1
        if counters["nodes"] > 250_000:
            raise ValueError("payload exceeds node limit")
        if depth > 32:
            raise ValueError("payload exceeds nesting limit")
        if isinstance(item, Mapping):
            if len(item) > 10_000:
                raise ValueError("payload mapping exceeds size limit")
            for key, child in item.items():
                if not isinstance(key, str):
                    raise TypeError("payload keys must be text")
                if key.casefold().replace("-", "_") in _FORBIDDEN_KEYS:
                    raise ValueError("payload contains a forbidden key")
                validate_agent_text(key)
                _walk(child, depth + 1)
        elif isinstance(item, (list, tuple)):
            if len(item) > 100_000:
                raise ValueError("payload list exceeds size limit")
            for child in item:
                _walk(child, depth + 1)
        elif isinstance(item, str):
            if len(item) > 100_000:
                raise ValueError("payload string exceeds size limit")
            validate_agent_text(item)
            if _ARBITRARY_LOCATION.search(item):
                raise ValueError("payload contains an arbitrary location")
        elif isinstance(item, (bytes, bytearray, set, frozenset)):
            raise TypeError("payload must contain bounded JSON values")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("payload contains a non-finite number")
        elif not isinstance(item, (int, float, bool, type(None))):
            raise TypeError("payload must contain bounded JSON values")

    _walk(value, 0)
    return value


__all__ = ["validate_agent_text", "validate_payload", "validate_untrusted_text"]
