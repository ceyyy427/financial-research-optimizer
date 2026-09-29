"""Build evidence-bound, non-causal explanations from saved research artifacts."""
from __future__ import annotations

from typing import Any

from .evidence_linker import link, source_ids
from .factor_attribution import explain_contributions
from .formula_registry import get_formula
from .scenario_explainer import explain_scenarios


def _metric_ids(data: dict[str, Any], *names: str) -> list[str]:
    metrics = data.get("result_lineage", {}).get("metrics", []) if isinstance(data.get("result_lineage"), dict) else []
    available = {str(item.get("metric_id")) for item in metrics if isinstance(item, dict)}
    return [name for name in names if name in available]


def _claim(data: dict[str, Any], *, claim_id: str, title: str, level: str, kind: str, statement: str, formula_id: str, artifact: str, metric_ids: list[str] | None = None, caveats: list[str] | None = None, next_check: str = "下一次数据刷新后复核") -> dict[str, Any]:
    context = link(data, artifact=artifact, metric_ids=metric_ids)
    artifact_key = artifact.rsplit("/", 1)[-1].replace(".json", "")
    has_artifact = artifact_key in data or artifact in (data.get("artifact_paths") or [])
    has_evidence = bool(has_artifact and context["evidence_refs"] and (context["calculation_refs"] or context["input_hash"]))
    status = "available" if has_evidence else "not_available"
    if not has_evidence:
        statement = "not_available：该结论没有足够的计算 lineage，不能从本次运行推出。"
    return {
        "claim_id": claim_id, "title": title, "claim_level": level, "claim_type": kind,
        "statement": statement, "formula_id": formula_id, "formula": get_formula(formula_id),
        "evidence_refs": context["evidence_refs"], "calculation_refs": context["calculation_refs"],
        "calculation_id": context["calculation_id"], "source_ids": context["source_ids"],
        "input_hash": context["input_hash"], "confidence": "available" if has_evidence else "not_available",
        "status": status, "caveats": caveats or ["预测解释描述模型如何使用输入，不自动构成因果结论。"], "next_check": next_check,
    }


def build_explanations(data: dict[str, Any]) -> list[dict[str, Any]]:
    forecast = data.get("forecast", {}) if isinstance(data.get("forecast"), dict) else {}
    model = str(forecast.get("model", ""))
    formula_id = "naive_last_value" if "naive" in model else "rolling_mean_forecast" if "rolling" in model else "historical_mean_forecast"
    claims = [
        _claim(data, claim_id="data_observation_001", title="数据发生了什么", level="observed", kind="data_observation", statement=f'本次运行读取了 {len(data.get("sources", []))} 个已登记来源；数据质量、PIT 和新鲜度状态必须结合 artifact 解读。', formula_id="status_gate", artifact="data_quality.json", caveats=["数据状态是观测与审计结果，不代表市场未来方向。"]),
        _claim(data, claim_id="forecast_model_001", title="模型如何得到预测", level="predictive", kind="model_mechanism", statement=f'当前选择模型为 {model or "未提供"}；它利用已保存的历史输入形成预测关系，不等同于因果关系。', formula_id=formula_id, artifact="analysis.json", metric_ids=_metric_ids(data, "baseline_mean", "forecast_rmse"), caveats=["未校准区间不能解释为覆盖概率", "制度变化可能使历史关系失效"], next_check="观察未来滚动窗口并更新校准状态"),
        _claim(data, claim_id="model_contribution_001", title="哪些因素推动了结果", level="predictive", kind="model_contribution", statement="模型贡献只能说明模型如何使用变量；当前 artifact 未提供可验证的贡献分解。", formula_id="status_gate", artifact="analysis.json", caveats=["特征贡献不等于因果效应。"]),
        _claim(data, claim_id="risk_explanation_001", title="风险为什么这样变化", level="decision", kind="risk_explanation", statement="组合风险由权重、协方差、尾部损失和交易成本共同决定；具体变化以 portfolio_robustness 与 tail_risk 为准。", formula_id="portfolio_objective", artifact="portfolio_robustness.json", metric_ids=_metric_ids(data, "portfolio_variance", "cvar"), caveats=["优化权重不是收益保证", "协方差和成本假设会改变解"]),
        _claim(data, claim_id="uncertainty_explanation_001", title="预测有多不确定", level="predictive", kind="uncertainty_explanation", statement=f'当前校准状态为 {forecast.get("calibration_status", "not_available")}，OOD 状态为 {forecast.get("ood_status", "not_available")}；没有校准证据时不应使用高置信度表述。', formula_id="prediction_interval", artifact="rolling_evaluation.json", metric_ids=_metric_ids(data, "coverage"), caveats=["残差区间不是自动校准的概率区间"]),
        _claim(data, claim_id="scenario_explanation_001", title="压力情景会怎样", level="decision", kind="scenario_explanation", statement="情景结果只能说明在给定扰动下模型和组合如何变化，不代表该情景一定发生。", formula_id="cvar", artifact="scenario_comparison.json", caveats=["情景输入必须有明确的变化量和 lineage"]),
        _claim(data, claim_id="failure_boundary_001", title="什么时候结论会失效", level="observed", kind="failure_boundary", statement="当数据新鲜度、PIT、校准、OOD 或约束状态不满足时，应降低结论等级或停止依赖分析。", formula_id="status_gate", artifact="monitoring_status.json", caveats=["这是研究门禁，不是市场因果判断"], next_check="下一次数据刷新或模型验证"),
        _claim(data, claim_id="causal_boundary_001", title="能否把结果解释成因果", level="predictive", kind="causal_hypothesis", statement="not_available：当前研究设计只提供预测关系或统计关联，没有足够的干预设计支持因果结论。", formula_id="status_gate", artifact="result_lineage.json", caveats=["不要把贡献、相关性或预测重要性写成因果影响"], next_check="若需要因果结论，先定义干预、混杂控制和识别假设"),
    ]
    contributions = data.get("factor_contributions") or data.get("feature_contributions")
    if isinstance(contributions, dict) and contributions:
        factor_rows = explain_contributions(contributions)
        claims[2]["statement"] = "模型贡献分解：" + "; ".join(f'{row["factor"]}={row["contribution"]}' for row in factor_rows)
        claims[2]["evidence_refs"] = ["analysis.json#/factor_contributions"]
        claims[2]["calculation_refs"] = claims[1]["calculation_refs"]
        claims[2]["calculation_id"] = claims[1]["calculation_id"]
        claims[2]["input_hash"] = claims[1]["input_hash"]
        claims[2]["source_ids"] = source_ids(data)
        claims[2]["confidence"] = "available"
        claims[2]["status"] = "available"
    else:
        claims[2]["statement"] = "not_available：没有保存的特征或因子贡献分解。"
        claims[2]["confidence"] = "not_available"
        claims[2]["status"] = "not_available"
    # A causal hypothesis requires a separate identification design even when
    # the run has ordinary predictive lineage.
    claims[7]["statement"] = "not_available：当前运行没有干预设计、混杂控制和识别假设，不能推出因果结论。"
    claims[7]["confidence"] = "not_available"
    claims[7]["status"] = "not_available"
    scenarios = data.get("scenarios")
    if isinstance(scenarios, list) and scenarios:
        claims[5]["statement"] = "; ".join(item["interpretation"] for item in explain_scenarios(scenarios) if item.get("interpretation"))
    return claims
