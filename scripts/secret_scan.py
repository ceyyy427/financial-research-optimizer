"""Small deterministic secret scan for the public source tree."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__", "node_modules"}
PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?:ghp|github_pat|xox[baprs])_[A-Za-z0-9_\-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part in SKIP_PARTS or part.startswith(".venv") for part in path.parts
        ):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ipynb"}:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: matched {pattern.pattern}")
    if findings:
        print("Potential secrets found:")
        print("\n".join(findings))
        return 1
    print("secret scan passed (no known credential patterns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
