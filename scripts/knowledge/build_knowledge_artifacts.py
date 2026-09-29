#!/usr/bin/env python3
"""Build explanations, learning cards and compiled formulas from saved artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .explanation_engine import build_explanations
    from .learning_cards import build_learning_cards
except ImportError:
    from scripts.knowledge.explanation_engine import build_explanations
    from scripts.knowledge.learning_cards import build_learning_cards
from scripts.tex.compile_formula import compile_formulas


def build(input_path: Path, output: Path) -> dict:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    explanations = build_explanations(data)
    cards = build_learning_cards(data, explanations)
    (output / "knowledge_explanations.json").write_text(json.dumps(explanations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "learning_cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = compile_formulas(None, output / "formulas")
    (output / "formula_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "completed", "knowledge_explanations": str(output / "knowledge_explanations.json"), "learning_cards": str(output / "learning_cards.json"), "formula_manifest": str(output / "formula_manifest.json"), "formula_render_status": manifest.get("render_status")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="saved analysis.json")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/knowledge"))
    args = parser.parse_args(argv)
    print(json.dumps(build(args.input, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
