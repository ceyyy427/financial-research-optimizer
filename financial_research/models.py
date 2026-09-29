"""Small, dependency-light public data models."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchRequest:
    task: str
    mode: str = "forecasting"
    output_level: str = "research_grade"
    universe: list[str] = field(default_factory=list)
    target: str | None = None
    horizon: str | int | None = None
    constraints: dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return {"schema_version": "1.0", **self.__dict__}


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    kind: str = "artifact"
    sha256: str | None = None

    def as_dict(self):
        return {"schema_version": "1.0", **self.__dict__}
