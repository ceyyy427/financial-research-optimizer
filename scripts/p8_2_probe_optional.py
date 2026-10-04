#!/usr/bin/env python3
"""Report optional P8.2 capabilities without modifying an environment.

The probe is intentionally read-only.  It is safe to run from the core or
quant environment and never imports optional research engines; isolated smoke
scripts may perform an explicit import after a human-reviewed installation.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path


def _module(name: str) -> dict[str, object]:
    try:
        present = importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        present = False
    version: str | None = None
    if present:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return {"module": name, "present": present, "version": version}


def collect(root: Path | None = None) -> dict[str, object]:
    project = root or Path(__file__).resolve().parents[1]
    return {
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "project": str(project),
        "python312": shutil.which("python3.12"),
        "node": shutil.which("node"),
        "npm": shutil.which("npm"),
        "optional_modules_in_current_env": [_module(name) for name in ("qlib", "vectorbt", "xtquant", "talib")],
        "isolated_envs": {
            name: {
                "path": str(project / path),
                "exists": (project / path).is_dir(),
            }
            for name, path in (("qlib", ".venv-qlib-py312"), ("vectorbt", ".venv-vectorbt"), ("qmt", ".venv-qmt"))
        },
        "frontend": {
            "package_lock": (project / "frontend" / "package-lock.json").is_file(),
            "bundle": (project / "site" / "assets" / "finathink-research.js").is_file(),
        },
    }


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2, sort_keys=True))
