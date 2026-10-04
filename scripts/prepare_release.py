"""Validate release metadata without creating a tag or publishing anything."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r'^version\s*=\s*"(0\.\d+\.\d+)"\s*$', re.MULTILINE)
TAG_RE = re.compile(r"^v(0\.\d+\.\d+)$")


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if match is None:
        raise SystemExit("pyproject.toml must contain a 0.x.y project version")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate metadata")
    parser.add_argument("--tag", help="validate a caller-provided v0.x.y tag")
    args = parser.parse_args()
    version = project_version()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version} - " not in changelog:
        raise SystemExit(f"CHANGELOG.md has no release heading for {version}")
    if args.tag is not None:
        tag_match = TAG_RE.fullmatch(args.tag)
        if tag_match is None or tag_match.group(1) != version:
            raise SystemExit(f"tag {args.tag!r} does not match project version {version}")
    if not args.check:
        print(f"release metadata is valid for v{version}; no tag was created")
    else:
        print(f"release metadata check passed for v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
