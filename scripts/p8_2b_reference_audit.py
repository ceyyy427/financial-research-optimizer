#!/usr/bin/env python3
"""Audit curated DOI metadata against Crossref without changing the catalog.

The default mode is offline and checks the local integrity contract. ``--live``
performs bounded metadata reads for DOI-backed records and exits non-zero when
the returned title/year/authors disagree with the local record. Live network
access is intentionally opt-in and is not part of deterministic CI.
"""

from __future__ import annotations

import argparse
import json
from urllib.parse import quote
from urllib.request import Request, urlopen

from finahinking.p8_2b.catalog import DEFAULT_KNOWLEDGE_CATALOG


def _fold(value: str) -> str:
    return " ".join(value.casefold().replace("…", "...").split())


def audit_live() -> list[str]:
    issues: list[str] = []
    for record in DEFAULT_KNOWLEDGE_CATALOG.references.records():
        if not record.doi:
            continue
        request = Request(
            f"https://api.crossref.org/works/{quote(record.doi, safe='')}",
            headers={"Accept": "application/json", "User-Agent": "Finathink citation audit"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                message = json.load(response).get("message", {})
        except Exception as exc:  # noqa: BLE001 - audit reports each bounded network failure
            issues.append(f"{record.reference_id}: Crossref lookup failed: {exc}")
            continue
        title = _fold(str((message.get("title") or [""])[0]))
        authors = _fold(" ".join(f"{item.get('given', '')} {item.get('family', '')}" for item in message.get("author", ())))
        year = ((message.get("published") or {}).get("date-parts") or [[None]])[0][0]
        if title != _fold(record.title):
            issues.append(f"{record.reference_id}: title mismatch ({title!r})")
        if not all(_fold(author) in authors for author in record.authors):
            issues.append(f"{record.reference_id}: author mismatch ({authors!r})")
        if year != record.year:
            issues.append(f"{record.reference_id}: year mismatch ({year!r})")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="query Crossref; otherwise run the offline catalog check")
    args = parser.parse_args()
    if args.live:
        issues = audit_live()
    else:
        records = DEFAULT_KNOWLEDGE_CATALOG.references
        issues = [f"missing local record: {reference_id}" for unit in DEFAULT_KNOWLEDGE_CATALOG.units for reference_id in unit.references if records.get(reference_id) is None]
    if issues:
        print("citation audit failed")
        print("\n".join(issues))
        return 1
    print(f"citation audit passed ({'live Crossref' if args.live else 'offline local cache'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
