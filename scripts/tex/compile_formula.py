#!/usr/bin/env python3
"""Build a provenance-preserving formula manifest and optionally compile TeX.

The command never claims a rendered formula exists when a TeX compiler is not
available.  This keeps mathematical explanations auditable in minimal installs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from scripts.knowledge.formula_registry import FORMULAS


def build_manifest(output: Path, formula_ids: list[str] | None = None) -> dict:
    selected = formula_ids or sorted(FORMULAS)
    formulas = [FORMULAS[item] for item in selected if item in FORMULAS]
    return {
        "schema_version": "1.0",
        "formula_count": len(formulas),
        "formulas": formulas,
        "render_status": "not_attempted",
        "compiler": None,
        "output": str(output),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/formula_manifest.json"))
    parser.add_argument("--tex", type=Path, help="Optional standalone TeX source to compile")
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args.output)
    if args.tex:
        compiler = shutil.which("tectonic") or shutil.which("pdflatex")
        if compiler:
            completed = subprocess.run([compiler, "-interaction=nonstopmode", str(args.tex)], capture_output=True, text=True)
            manifest["compiler"] = Path(compiler).name
            manifest["render_status"] = "passed" if completed.returncode == 0 else "failed"
            manifest["compiler_output"] = (completed.stdout + completed.stderr)[-2000:]
        else:
            manifest["render_status"] = "not_available"
            manifest["reason"] = "tectonic or pdflatex is not installed"
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["render_status"] in {"passed", "not_attempted", "not_available"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
