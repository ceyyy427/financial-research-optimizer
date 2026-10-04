"""Evidence-linked community contracts and an inert untrusted-content boundary.

The community surface is deliberately content-as-data.  A post, claim, or
summary can be displayed, indexed, or reviewed, but this module never treats
its text as Python, SQL, shell, browser input, or model instructions.  Truth
and source authority remain with the P6.5/P6.6 records and the P7 repository.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

_CLAIM_TYPES = {"FACT", "INTERPRETATION", "HYPOTHESIS", "QUANT_FINDING", "UNKNOWN", "LIMITATION"}
_ATTACHMENT_ROLES = {"support", "counter_evidence", "context"}
_PROMPT_PATTERNS = (
    re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?\b"),
    re.compile(r"(?i)\b(?:system|developer)\s+message\b"),
    re.compile(r"(?i)\bdo\s+not\s+follow\s+the\s+user\b"),
)
_TOOL_PATTERN = re.compile(
    r"(?is)\b(?:tool|function|exec|shell|terminal|browser|python)\s*"
    r"(?:call|invoke|run)?\s*[:(][^\n<>]{0,800}\)?"
)
_COMMAND_PATTERN = re.compile(r"(?is)\b(?:rm\s+-rf|curl|wget|powershell|bash|sh)\b[^\n<>]{0,400}")
_DANGEROUS_LINK_PATTERN = re.compile(r"(?i)\b(?:javascript|vbscript|data):[^\s\"'<>)]*")
_TAG_PATTERN = re.compile(r"(?is)<[^>]*>")
_SCRIPT_PATTERN = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _tuple_text(values: Iterable[str], label: str) -> tuple[str, ...]:
    try:
        result = tuple(_text(value, label) for value in values)
    except TypeError as exc:
        raise TypeError(f"{label} must be a sequence") from exc
    if len(set(result)) != len(result):
        raise ValueError(f"{label} values must be unique")
    return result


class CommunityIntegrityError(ValueError):
    """A typed community claim or attachment failed an integrity check."""


@dataclass(frozen=True)
class CommunityClaim:
    """A claim that remains distinct from its supporting evidence."""

    claim_id: str
    post_id: str
    claim_type: str
    statement: str
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    status: str = "active"

    def __post_init__(self) -> None:
        for name in ("claim_id", "post_id", "statement"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        label = _text(self.claim_type, "claim_type").upper()
        if label not in _CLAIM_TYPES:
            raise CommunityIntegrityError("claim_type is invalid")
        object.__setattr__(self, "claim_type", label)
        evidence = _tuple_text(self.evidence_ids, "evidence_id")
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))
        if self.status not in {"active", "withdrawn", "disputed"}:
            raise CommunityIntegrityError("claim status is invalid")
        if label in {"FACT", "QUANT_FINDING"} and not evidence:
            raise CommunityIntegrityError("fact-like claims require evidence")

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "post_id": self.post_id,
            "claim_type": self.claim_type,
            "statement": self.statement,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "status": self.status,
        }


@dataclass(frozen=True)
class EvidenceAttachment:
    """A typed link from a community post/claim to an evidence projection."""

    attachment_id: str
    post_id: str
    claim_id: str
    projection_id: str
    role: str = "support"
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("attachment_id", "post_id", "claim_id", "projection_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.role not in _ATTACHMENT_ROLES:
            raise CommunityIntegrityError("attachment role is invalid")
        object.__setattr__(self, "evidence_ids", _tuple_text(self.evidence_ids, "evidence_id"))

    def to_dict(self) -> dict[str, object]:
        return {
            "attachment_id": self.attachment_id,
            "post_id": self.post_id,
            "claim_id": self.claim_id,
            "projection_id": self.projection_id,
            "role": self.role,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class CommunitySummary:
    """A discussion summary with uncertainty and disagreement first-class."""

    agreed: tuple[str, ...]
    disagreements: tuple[str, ...]
    evidence_for_view_a: tuple[str, ...]
    evidence_for_view_b: tuple[str, ...]
    unknown: tuple[str, ...]
    test_next: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "agreed",
            "disagreements",
            "evidence_for_view_a",
            "evidence_for_view_b",
            "unknown",
            "test_next",
        ):
            object.__setattr__(self, name, _tuple_text(getattr(self, name), name))
        if not self.unknown:
            raise CommunityIntegrityError("discussion summaries must preserve unknowns")
        if not self.test_next:
            raise CommunityIntegrityError("discussion summaries must preserve a test-next item")

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "agreed": list(self.agreed),
            "disagreements": list(self.disagreements),
            "evidence_for_view_a": list(self.evidence_for_view_a),
            "evidence_for_view_b": list(self.evidence_for_view_b),
            "unknown": list(self.unknown),
            "test_next": list(self.test_next),
        }

    # Human-facing aliases keep the contract readable in UI code while the
    # serialized names stay stable and explicit.
    @property
    def agree(self) -> tuple[str, ...]:
        return self.agreed

    @property
    def disagree(self) -> tuple[str, ...]:
        return self.disagreements

    @property
    def evidence_for_a(self) -> tuple[str, ...]:
        return self.evidence_for_view_a

    @property
    def evidence_for_b(self) -> tuple[str, ...]:
        return self.evidence_for_view_b


def summarize_discussion(
    *,
    agreed: Iterable[str],
    disagreements: Iterable[str],
    evidence_for_view_a: Iterable[str],
    evidence_for_view_b: Iterable[str],
    unknown: Iterable[str],
    test_next: Iterable[str],
) -> CommunitySummary:
    """Build a transparent summary; this function never infers consensus."""

    def clean(values: Iterable[str]) -> tuple[str, ...]:
        # Summary sections are still community text.  Keep the output inert
        # even when a caller forwards untrusted post text into a section.
        return tuple(sanitize_untrusted_content(value).text for value in values)

    return CommunitySummary(
        clean(agreed),
        clean(disagreements),
        clean(evidence_for_view_a),
        clean(evidence_for_view_b),
        clean(unknown),
        clean(test_next),
    )


@dataclass(frozen=True)
class SanitizedCommunityContent:
    """Safe display text plus boundary telemetry; no executable representation."""

    text: str
    warnings: tuple[str, ...] = ()
    contains_prompt_injection: bool = False
    contains_tool_directive: bool = False
    blocked_links: int = 0
    truncated: bool = False


def sanitize_untrusted_content(value: str, *, max_length: int = 20_000) -> SanitizedCommunityContent:
    """Remove markup/directive payloads while preserving benign visible text.

    This is a display boundary, not a truth or moderation classifier.  The
    return value is inert text and metadata only; no URL is fetched and no
    tool/parser is dispatched from community content.
    """

    if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length < 1 or max_length > 100_000:
        raise ValueError("max_length must be between one and 100000")
    raw = _text(value, "community content")
    normalized = unicodedata.normalize("NFKC", raw)
    normalized = html.unescape(normalized)
    # Remove C0 controls and Unicode format/bidi controls before matching
    # directives; otherwise an attacker can hide an instruction with a zero
    # width or right-to-left override character.
    normalized = "".join(
        character
        if character in {"\n", "\r", "\t"} or unicodedata.category(character) not in {"Cc", "Cf"}
        else " "
        for character in normalized
    )
    prompt = any(pattern.search(normalized) for pattern in _PROMPT_PATTERNS)
    tool = bool(_TOOL_PATTERN.search(normalized) or _COMMAND_PATTERN.search(normalized))
    blocked_matches = _DANGEROUS_LINK_PATTERN.findall(normalized)
    body = _DANGEROUS_LINK_PATTERN.sub("[blocked-link]", normalized)
    for pattern in _PROMPT_PATTERNS:
        body = pattern.sub("[untrusted-instruction]", body)
    body = _TOOL_PATTERN.sub("[untrusted-tool-directive]", body)
    body = _COMMAND_PATTERN.sub("[untrusted-command]", body)
    body = _SCRIPT_PATTERN.sub(" ", body)
    body = _TAG_PATTERN.sub(" ", body)
    body = html.unescape(body)
    body = _CONTROL_PATTERN.sub(" ", body)
    body = re.sub(r"[ \t]+", " ", body).strip()
    truncated = len(body) > max_length
    if truncated:
        body = body[:max_length].rstrip() + "…"
    warnings: list[str] = []
    if prompt:
        warnings.append("prompt_injection_text_detected")
    if tool:
        warnings.append("tool_directive_text_detected")
    if blocked_matches:
        warnings.append("dangerous_link_blocked")
    if truncated:
        warnings.append("content_truncated")
    return SanitizedCommunityContent(
        text=body,
        warnings=tuple(warnings),
        contains_prompt_injection=prompt,
        contains_tool_directive=tool,
        blocked_links=len(blocked_matches),
        truncated=truncated,
    )


class CommunityIntegrityService:
    """Pure checks that complement repository authorization decisions."""

    def __init__(self, repository: object | None = None) -> None:
        # The repository is optional so the value-level checks remain easy to
        # exercise without persistence.  When supplied, all writes still go
        # through its authenticated methods; this class never issues SQL.
        self.repository = repository

    @staticmethod
    def validate_claim(claim: CommunityClaim, *, available_evidence: Iterable[str]) -> CommunityClaim:
        if not isinstance(claim, CommunityClaim):
            raise TypeError("claim must be a CommunityClaim")
        available = set(_tuple_text(available_evidence, "evidence_id"))
        missing = set(claim.evidence_ids) - available
        if missing:
            raise CommunityIntegrityError(f"claim references unavailable evidence: {sorted(missing)}")
        return claim

    @staticmethod
    def validate_attachment(attachment: EvidenceAttachment, claim: CommunityClaim) -> EvidenceAttachment:
        if not isinstance(attachment, EvidenceAttachment):
            raise TypeError("attachment must be an EvidenceAttachment")
        if not isinstance(claim, CommunityClaim):
            raise TypeError("claim must be a CommunityClaim")
        if attachment.post_id != claim.post_id or attachment.claim_id != claim.claim_id:
            raise CommunityIntegrityError("attachment does not belong to claim post")
        if any(item not in claim.evidence_ids for item in attachment.evidence_ids):
            raise CommunityIntegrityError("attachment evidence is not linked by claim")
        if claim.claim_type in {"FACT", "QUANT_FINDING"} and not attachment.evidence_ids:
            raise CommunityIntegrityError("fact-like claim attachment requires evidence")
        return attachment

    @staticmethod
    def sanitize_post_text(title: str, body: str) -> tuple[SanitizedCommunityContent, SanitizedCommunityContent]:
        return sanitize_untrusted_content(title, max_length=500), sanitize_untrusted_content(body)

    def create_post(self, session_id: str, post: object, claim: CommunityClaim, *, available_evidence: Iterable[str]) -> object:
        """Sanitize then persist a typed post through the repository boundary."""

        if self.repository is None:
            raise RuntimeError("a repository is required to persist a post")
        from .models import CommunityPost

        if not isinstance(post, CommunityPost):
            raise TypeError("post must be a CommunityPost")
        self.validate_claim(claim, available_evidence=available_evidence)
        if claim.post_id != post.post_id or claim.claim_type != post.claim_type:
            raise CommunityIntegrityError("claim does not match post identity or label")
        title, body = self.sanitize_post_text(post.title, post.body)
        sanitized_post = CommunityPost(post.post_id, post.room_id, post.author_id, post.claim_type, title.text, body.text, post.status)
        self.repository.create_post(session_id, sanitized_post)
        return sanitized_post

    def attach_evidence(self, session_id: str, attachment: EvidenceAttachment, claim: CommunityClaim) -> EvidenceAttachment:
        """Validate claim linkage then invoke the repository's author check."""

        if self.repository is None:
            raise RuntimeError("a repository is required to attach evidence")
        self.validate_attachment(attachment, claim)
        self.repository.attach_projection(session_id, attachment.post_id, attachment.projection_id, attachment.role)
        return attachment


__all__ = [
    "CommunityClaim",
    "CommunityIntegrityError",
    "CommunityIntegrityService",
    "CommunitySummary",
    "EvidenceAttachment",
    "SanitizedCommunityContent",
    "sanitize_untrusted_content",
    "summarize_discussion",
]
