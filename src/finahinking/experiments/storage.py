from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .models import ResearchRun


class RunStore:
    _SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        if not self._SAFE_ID.fullmatch(run_id):
            raise ValueError("run id is invalid")
        return self.root / f"{run_id}.json"

    def save(self, run: ResearchRun) -> Path:
        path = self._path(run.run_id)
        if path.exists() and self.load(run.run_id) != run:
            raise ValueError("a different run already exists")
        fd, temporary = tempfile.mkstemp(prefix=f".{run.run_id}.", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(run.to_json())
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path

    def load(self, run_id: str) -> ResearchRun:
        path = self._path(run_id)
        try:
            return ResearchRun.from_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"research run not found: {run_id}") from exc
