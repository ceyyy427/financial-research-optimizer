#!/usr/bin/env python3
"""Compile registered research formulas into local, hashable assets."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
from pathlib import Path

try:
    from scripts.knowledge.formula_registry import FORMULAS
except ImportError:
    from knowledge.formula_registry import FORMULAS

STATUSES = {"not_attempted", "compiling", "compiled", "blocked", "failed", "not_available"}


def _formula_ids(input_path: Path | None):
    if not input_path:
        return sorted(FORMULAS)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    claims = payload.get("knowledge_explanations", []) if isinstance(payload, dict) else payload
    found = []
    if isinstance(payload, dict):
        found.extend(payload.get("formula_ids", []))
        cards = payload.get("learning_cards", {}).get("cards", [])
        found.extend(item.get("formula_id") for item in cards if isinstance(item, dict))
    found.extend(item.get("formula_id") for item in claims if isinstance(item, dict))
    return sorted({item for item in found if item}) or sorted(FORMULAS)


def _tex_source(formula):
    return "\\documentclass[preview]{standalone}\n\\usepackage{amsmath,amssymb}\n\\begin{document}\n$" + formula.get("tex", "") + "$\n\\end{document}\n"


def _mathml(formula: dict) -> str:
    # This is an accessible, offline fallback representation. It intentionally
    # does not pretend to parse TeX into semantic MathML.
    value = html.escape(str(formula.get("tex", "")))
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML"><mtext>{value}</mtext></math>\n'


def _version(compiler: str | None) -> str | None:
    if not compiler:
        return None
    result = subprocess.run([compiler, "--version"], capture_output=True, text=True, check=False)
    lines = (result.stdout or result.stderr).splitlines()
    return lines[0] if lines else "unknown"


def compile_formulas(input_path: Path | None, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which("tectonic") or shutil.which("xelatex") or shutil.which("pdflatex")
    converter = shutil.which("dvisvgm") or shutil.which("pdf2svg")
    records = []
    any_failed = False
    any_blocked = False
    for formula_id in _formula_ids(input_path):
        formula = dict(FORMULAS.get(formula_id, {"formula_id": formula_id, "tex": "", "alt_text": "公式不可用", "variables": {}}))
        tex_path = output / f"{formula_id}.tex"
        mathml_path = output / f"{formula_id}.mathml"
        tex_path.write_text(_tex_source(formula), encoding="utf-8")
        mathml_path.write_text(_mathml(formula), encoding="utf-8")
        record = {**formula, "source_knowledge_id": formula.get("source_knowledge_id"), "tex_source": tex_path.name, "compiled_asset": None, "mathml_asset": mathml_path.name, "compiler": Path(compiler).name if compiler else None, "compiler_version": _version(compiler), "sha256": "sha256:" + hashlib.sha256(tex_path.read_bytes()).hexdigest(), "status": "not_attempted", "reason_code": None}
        if not compiler:
            record.update(status="not_available", reason_code="FORMULA_COMPILE_FAILED")
            any_blocked = True
            records.append(record)
            continue
        record["status"] = "compiling"
        result = subprocess.run([compiler, "-interaction=nonstopmode", tex_path.name], cwd=output, capture_output=True, text=True, check=False)
        pdf_path = output / f"{formula_id}.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            record.update(status="failed", reason_code="FORMULA_COMPILE_FAILED")
            any_failed = True
            records.append(record)
            continue
        if not converter:
            record.update(status="blocked", reason_code="FORMULA_RENDER_FAILED")
            any_blocked = True
            records.append(record)
            continue
        svg_path = output / f"{formula_id}.svg"
        command = [converter, str(pdf_path), str(svg_path)] if Path(converter).name == "pdf2svg" else [converter, "--pdf", str(pdf_path), "--output", str(svg_path)]
        converted = subprocess.run(command, capture_output=True, text=True, check=False)
        if converted.returncode != 0 or not svg_path.exists():
            record.update(status="failed", reason_code="FORMULA_RENDER_FAILED")
            any_failed = True
            records.append(record)
            continue
        record.update(compiled_asset=svg_path.name, status="compiled", sha256="sha256:" + hashlib.sha256(svg_path.read_bytes()).hexdigest())
        records.append(record)
    if not records:
        render_status, reason_code = "not_available", "FORMULA_REGISTRY_EMPTY"
    elif any_failed:
        render_status, reason_code = "failed", "FORMULA_COMPILE_FAILED" if any(item.get("reason_code") == "FORMULA_COMPILE_FAILED" for item in records) else "FORMULA_RENDER_FAILED"
    elif any_blocked:
        render_status, reason_code = "blocked", "FORMULA_COMPILE_FAILED" if not compiler else "FORMULA_RENDER_FAILED"
    elif all(item["status"] == "compiled" for item in records):
        render_status, reason_code = "compiled", None
    else:
        render_status, reason_code = "not_available", "FORMULA_NOT_AVAILABLE"
    manifest = {"schema_version": "1.0", "formula_count": len(records), "formulas": records, "render_status": render_status, "compiler": Path(compiler).name if compiler else None, "output": str(output), "reason": reason_code, "reason_code": reason_code}
    (output / "formula_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_manifest(output: Path, formula_ids: list[str] | None = None) -> dict:
    """Compatibility helper: explicitly declares that no compilation was attempted."""
    selected = formula_ids or sorted(FORMULAS)
    formulas = []
    for item in selected:
        if item not in FORMULAS:
            continue
        formulas.append({**FORMULAS[item], "source": None, "source_knowledge_id": FORMULAS[item].get("source_knowledge_id"), "tex_source": None, "compiled_asset": None, "mathml_asset": None, "compiler": None, "compiler_version": None, "sha256": "", "status": "not_attempted", "reason_code": None})
    return {"schema_version": "1.0", "formula_count": len(formulas), "formulas": formulas, "render_status": "not_attempted", "compiler": None, "output": str(output), "reason": None, "reason_code": None}


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
