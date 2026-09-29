import asyncio
import json
from pathlib import Path

from jsonschema import validate

from mcp_server.tools import ResearchMcpService
from scripts.knowledge.explanation_engine import build_explanations
from scripts.knowledge.learning_cards import build_learning_cards
from scripts.tex.compile_formula import build_manifest


def test_explanations_and_learning_cards_are_evidence_bound(ROOT):
    data = {"forecast": {"model": "rolling_mean_baseline", "calibration_status": "uncalibrated", "ood_status": "not_checked"}, "sources": []}
    claims = build_explanations(data)
    cards = build_learning_cards(data, claims)
    claim_schema = json.loads((ROOT / "schemas/knowledge_explanation.schema.json").read_text(encoding="utf-8"))
    card_schema = json.loads((ROOT / "schemas/learning_cards.schema.json").read_text(encoding="utf-8"))
    for claim in claims:
        validate(claim, claim_schema)
    validate(cards, card_schema)
    assert {item["claim_type"] for item in claims} == {"data_observation", "model_mechanism", "model_contribution", "risk_explanation", "uncertainty_explanation", "scenario_explanation", "failure_boundary", "causal_hypothesis"}
    assert all(item["status"] == "not_available" for item in claims if item["claim_type"] in {"model_contribution", "causal_hypothesis"})
    assert all(item["numeric_example"]["status"] == "not_available" for item in cards["cards"])


def test_formula_compatibility_manifest_never_claims_compiled(tmp_path):
    manifest = build_manifest(tmp_path, ["rmse"])
    assert manifest["render_status"] == "not_attempted"
    assert manifest["formulas"][0]["status"] == "not_attempted"
    schema = json.loads(Path("schemas/formula_manifest.schema.json").read_text(encoding="utf-8"))
    validate(manifest, schema)


def test_mcp_formula_and_provenance_return_learning_fields(tmp_path):
    async def run():
        service = ResearchMcpService(run_root=str(tmp_path))
        run_id = service.store.create("knowledge", "forecasting", "standard")
        service.store.write_json(run_id, "formula_manifest.json", {"schema_version": "1.0", "formula_count": 1, "render_status": "blocked", "formulas": [{"formula_id": "rmse", "tex": "x", "alt_text": "RMSE", "variables": {}, "compiled_asset": None, "mathml_asset": "rmse.mathml", "compiler": None, "compiler_version": None, "sha256": "sha256:x", "status": "blocked"}]})
        service.store.write_json(run_id, "knowledge_explanations.json", [{"claim_id": "rmse_metric", "formula_id": "rmse", "evidence_refs": ["rolling_evaluation.json#/models"], "calculation_refs": ["calc_1"], "source_ids": ["synthetic"], "input_hash": "abc"}])
        service.store.write_json(run_id, "learning_cards.json", {"schema_version": "1.0", "card_count": 1, "cards": [{"card_id": "rmse_metric", "formula_id": "rmse", "evidence_refs": ["rolling_evaluation.json"], "lineage_refs": ["calc_1"], "source_ids": ["synthetic"]}]})
        formula = await service.get_formula("rmse", run_id=run_id)
        explanation = await service.explain_metric(run_id, "rmse", admin=True)
        assert formula["compiled_asset"] is None
        assert formula["render_status"] == "blocked"
        assert explanation["learning_cards"]
        assert explanation["evidence_refs"]
    asyncio.run(run())
