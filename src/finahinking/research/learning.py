"""Append-only, as-of bounded learning evidence store."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from .contracts import AgentReport, DecisionCard, stable_digest, to_jsonable

_SECRET = re.compile(r"(?i)(?:api[_-]?key|token|secret|password|endpoint)\s*[=:]")
_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:[\\/])")


def _as_date(value: date | str) -> date:
    if isinstance(value, str):
        value = date.fromisoformat(value)
    if not isinstance(value, date):
        raise TypeError("as_of must be a date")
    return value


@dataclass(frozen=True, slots=True)
class LearningEntry:
    entry_id: str
    created_at: datetime | str
    as_of: date | str
    instrument_scope: tuple[str, ...]
    lesson_type: str
    claim: str
    evidence_refs: tuple[str, ...]
    source_run_id: str
    status: str

    def __post_init__(self) -> None:
        if not self.entry_id.strip() or not self.source_run_id.strip():
            raise ValueError("entry_id and source_run_id must be non-empty")
        created = self.created_at
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        object.__setattr__(self, "created_at", created.astimezone(UTC))
        object.__setattr__(self, "as_of", _as_date(self.as_of))
        object.__setattr__(self, "instrument_scope", tuple(str(item).strip() for item in self.instrument_scope if str(item).strip()))
        for name in ("lesson_type", "claim", "status"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "evidence_refs", tuple(str(item).strip() for item in self.evidence_refs if str(item).strip()))


def validate_learning_entry(entry: LearningEntry) -> None:
    if not isinstance(entry, LearningEntry):
        raise TypeError("entry must be LearningEntry")
    if entry.as_of > entry.created_at.date():
        raise ValueError("entry as_of is in the future")
    if not entry.evidence_refs:
        raise ValueError("learning entry requires evidence refs")
    if not entry.source_run_id.strip():
        raise ValueError("learning entry requires source run")
    text = " ".join((entry.claim, *entry.instrument_scope, *entry.evidence_refs))
    if _SECRET.search(text):
        raise ValueError("learning entry contains secret")
    if _PATH.search(text):
        raise ValueError("learning entry contains a path")


class LearningStore:
    def __init__(self, path: str | Path, *, current_as_of: date | str | None = None) -> None:
        self.path = Path(path)
        self.current_as_of = _as_date(current_as_of) if current_as_of is not None else None
        self._entries: dict[str, LearningEntry] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    payload = json.loads(line)
                    entry = LearningEntry(**payload)
                    validate_learning_entry(entry)
                    self._entries[entry.entry_id] = entry

    def record_evidence(self, entry: LearningEntry) -> LearningEntry:
        validate_learning_entry(entry)
        if self.current_as_of is not None and entry.as_of > self.current_as_of:
            raise ValueError("entry as_of is in the future")
        if entry.entry_id in self._entries:
            raise ValueError(f"duplicate learning entry: {entry.entry_id}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(to_jsonable(entry), ensure_ascii=False, sort_keys=True) + "\n")
        self._entries[entry.entry_id] = entry
        return entry

    def inspect_asof_lessons(self, as_of: date | str, scope: Sequence[str] = ()) -> tuple[LearningEntry, ...]:
        cutoff = _as_date(as_of)
        requested_scope = set(scope)
        entries = [
            entry
            for entry in self._entries.values()
            if entry.as_of <= cutoff and (not requested_scope or requested_scope.intersection(entry.instrument_scope))
        ]
        return tuple(sorted(entries, key=lambda item: (item.as_of, item.entry_id)))

    def digest(self) -> str:
        return stable_digest(tuple(self._entries[key] for key in sorted(self._entries)))


def reconcile_learning(
    run_id: str,
    reports: Sequence[AgentReport],
    decision: DecisionCard,
    as_of: date | str,
) -> tuple[LearningEntry, ...]:
    as_of_date = _as_date(as_of)
    created_at = datetime.combine(as_of_date + timedelta(days=1), time.min, tzinfo=UTC)
    instruments = tuple(sorted(decision.weights))
    entries: list[LearningEntry] = []
    for report in reports:
        if report.status == "FAILED" or not report.evidence_refs:
            continue
        for index, claim in enumerate(report.claims):
            candidate = LearningEntry(
                entry_id=f"{run_id}:{report.role}:{index}",
                created_at=created_at,
                as_of=as_of_date,
                instrument_scope=instruments,
                lesson_type=f"analyst:{report.role}",
                claim=claim,
                evidence_refs=report.evidence_refs,
                source_run_id=run_id,
                status="RECORDED",
            )
            validate_learning_entry(candidate)
            entries.append(candidate)
    return tuple(entries)

