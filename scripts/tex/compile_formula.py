#!/usr/bin/env python3
"""Compile explainable research formulas into local, hashable assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from scripts.knowledge.formula_registry import FORMULAS


def _formula_ids(input_path: Path | None):
    if not input_path:
        return sorted(FORMULAS)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    claims = payload.get("knowledge_explanations", payload) if isinstance(payload, dict) else payload
    found = [claim.get("formula_id") for claim in claims if isinstance(claim, dict) and claim.get("formula_id")]
    return sorted(set(found)) or sorted(FORMULAS)


def _tex_source(formula):
    return "\\documentclass[preview]{standalone}\n\\usepackage{amsmath,amssymb}\n\\begin{document}\n$" + formula.get("tex", "") + "$\n\\end{document}\n"


def compile_formulas(input_path: Path | None, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which("tectonic") or shutil.which("xelatex") or shutil.which("pdflatex")
    records = []
    blocked_reason = None
    for formula_id in _formula_ids(input_path):
        formula = FORMULAS.get(formula_id, {"formula_id": formula_id, "tex": "", "alt_text": "公式不可用", "variables": {}})
        tex_path = output / f"{formula_id}.tex"
        tex_path.write_text(_tex_source(formula), encoding="utf-8")
        record = {**formula, "tex_source": tex_path.name, "compiled_asset": None, "compiler": Path(compiler).name if compiler else None, "compiler_version": None, "sha256": hashlib.sha256(tex_path.read_bytes()).hexdigest(), "status": "blocked"}
        if not compiler:
            blocked_reason = "FORMULA_COMPILE_FAILED"
            records.append(record)
            continue
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True).stdout.splitlines()
        record["compiler_version"] = version[0] if version else "unknown"
        result = subprocess.run([compiler, "-interaction=nonstopmode", tex_path.name], cwd=output, capture_output=True, text=True)
        pdf_path = output / f"{formula_id}.pdf"
        converter = shutil.which("dvisvgm") or shutil.which("pdf2svg")
        if result.returncode == 0 and pdf_path.exists() and converter:
            svg_path = output / f"{formula_id}.svg"
            command = [converter, str(pdf_path), str(svg_path)] if Path(converter).name == "pdf2svg" else [converter, "--pdf", str(pdf_path), "--output", str(svg_path)]
            converted = subprocess.run(command, capture_output=True, text=True)
            if converted.returncode == 0 and svg_path.exists():
                record.update({"compiled_asset": svg_path.name, "status": "compiled", "sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest()})
            else:
                blocked_reason = "FORMULA_RENDER_FAILED"
        else:
            blocked_reason = "FORMULA_COMPILE_FAILED"
        records.append(record)
    status = "compiled" if records and all(item["status"] == "compiled" for item in records) else "blocked"
    manifest = {"schema_version": "1.0", "formula_count": len(records), "formulas": records, "render_status": status, "compiler": Path(compiler).name if compiler else None, "reason_code": blocked_reason}
    (output / "formula_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_manifest(output: Path, formula_ids: list[str] | None = None) -> dict:
    """Compatibility helper for artifact generation without compilation."""
    selected = formula_ids or sorted(FORMULAS)
    formulas = [FORMULAS[item] for item in selected if item in FORMULAS]
    return {"schema_version": "1.0", "formula_count": len(formulas), "formulas": formulas, "render_status": "not_attempted", "compiler": None, "output": str(output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/formulas"))
    args = parser.parse_args(argv)
    manifest = compile_formulas(args.input, args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["render_status"] == "compiled" else 2


if __name__ == "__main__":
    raise SystemExit(main())
