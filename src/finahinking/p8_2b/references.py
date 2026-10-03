"""Offline-first bibliographic metadata and deterministic citation exports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

_DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("DOI is required")
    doi = value.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:").strip()
    if not _DOI.fullmatch(doi):
        raise ValueError("DOI is invalid")
    return doi.lower()


@dataclass(frozen=True)
class ReferenceRecord:
    reference_id: str
    title: str
    authors: tuple[str, ...]
    year: int
    reference_type: str
    role: str
    doi: str | None
    url: str
    publisher: str
    source: str
    notes: str
    open_access_url: str | None = None

    def __post_init__(self) -> None:
        for name in ("reference_id", "title", "reference_type", "role", "url", "publisher", "source", "notes"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value.strip())
        if any(not isinstance(author, str) or not author.strip() for author in self.authors):
            raise ValueError("authors are required")
        object.__setattr__(self, "authors", tuple(author.strip() for author in self.authors))
        if not isinstance(self.year, int) or not 1400 <= self.year <= 2100:
            raise ValueError("year is invalid")
        if self.doi is not None:
            object.__setattr__(self, "doi", normalize_doi(self.doi))

    def to_dict(self) -> dict[str, object]:
        return {"reference_id": self.reference_id, "title": self.title, "authors": list(self.authors), "year": self.year, "reference_type": self.reference_type, "role": self.role, "doi": self.doi, "url": self.url, "publisher": self.publisher, "source": self.source, "notes": self.notes, "open_access_url": self.open_access_url}

    def to_csl_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"id": self.reference_id, "title": self.title, "author": [{"literal": author} for author in self.authors], "issued": {"date-parts": [[self.year]]}, "type": self.reference_type.casefold(), "publisher": self.publisher, "URL": self.url}
        if self.doi:
            payload["DOI"] = self.doi
        return payload

    def bibtex(self) -> str:
        authors = " and ".join(self.authors)
        doi_line = f",\n  doi = {{{self.doi}}}" if self.doi else ""
        return f"@article{{{self.reference_id},\n  author = {{{authors}}},\n  title = {{{self.title}}},\n  year = {{{self.year}}},\n  publisher = {{{self.publisher}}}{doi_line}\n}}"


class LocalReferenceCache:
    def __init__(self, records: tuple[ReferenceRecord, ...] = ()) -> None:
        self._records: dict[str, ReferenceRecord] = {}
        for record in records:
            if record.reference_id in self._records:
                raise ValueError("duplicate reference_id")
            self._records[record.reference_id] = record
            if record.doi and any(item.doi == record.doi for item in self._records.values() if item.reference_id != record.reference_id):
                raise ValueError("duplicate DOI")

    def get(self, key: str) -> ReferenceRecord | None:
        value = key.strip()
        if _DOI.fullmatch(value.removeprefix("https://doi.org/")):
            doi = normalize_doi(value)
            return next((record for record in self._records.values() if record.doi == doi), None)
        return self._records.get(value)

    def records(self) -> tuple[ReferenceRecord, ...]:
        return tuple(self._records.values())

    def to_json(self) -> str:
        return json.dumps([record.to_dict() for record in self._records.values()], sort_keys=True, indent=2)
