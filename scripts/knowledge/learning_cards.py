"""Generate artifact-bound learning cards; absent evidence stays not_available."""
from __future__ import annotations

from typing import Any

from .evidence_linker import link
from .formula_registry import get_formula
from .knowledge_registry import get_knowledge
from .lesson_engine import build_lesson


def _card(data: dict[str, Any], *, card_id: str, concept: str, category: str, formula_id: str | None, artifact: str, refs: list[str], derivation: list[str], applicability: list[str], failure: list[str], test: list[str], knowledge_id: str | None = None) -> dict[str, Any]:
    ctx = link(data, artifact=artifact, metric_ids=refs)
    knowledge = get_knowledge(knowledge_id or formula_id or "")
    artifact_key = artifact.rsplit("/", 1)[-1].replace(".json", "")
    available = bool(artifact_key in data and (ctx["calculation_refs"] or ctx["input_hash"]))
    formula = get_formula(formula_id) if formula_id else {}
    return {
        "card_id": card_id, "concept": concept, "category": category,
        "formula_id": formula_id, "formula": formula, "variables": formula.get("variables", {}),
        "derivation_steps": derivation,
        "numeric_example": {"status": "available" if available else "not_available", "values": {} if not available else {item.get("metric_id"): item.get("value") for item in ctx["matched_metrics"]}, "interpretation": "仅展示已保存 lineage 的数值；没有数值时不猜测。"},
        "applicability": applicability, "failure_boundaries": failure, "self_test": test,
        "evidence_refs": ctx["evidence_refs"], "lineage_refs": ctx["calculation_refs"], "knowledge_refs": [knowledge.get("knowledge_id", knowledge_id or "")],
        "source_ids": ctx["source_ids"], "input_hash": ctx["input_hash"], "status": "available" if available else "not_available",
    }


def build_learning_cards(data: dict[str, Any], explanations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cards = [
        _card(data, card_id="model_mechanism", concept="当前模型机制", category="model", formula_id="rolling_mean_forecast", artifact="analysis.json", refs=["baseline_mean", "forecast_rmse"], derivation=["读取预测 origin 之前的观测", "按模型公式形成点预测", "用滚动评估比较候选模型"], applicability=["目标变量和时间顺序已定义", "评估窗口是样本外"], failure=["结构突变", "窗口敏感", "未来数据泄漏"], test=["为什么滚动窗口变短会更敏感？", "当前模型是否经过样本外比较？"], knowledge_id="rolling_mean"),
        _card(data, card_id="rmse_metric", concept="RMSE 如何衡量误差", category="evaluation", formula_id="rmse", artifact="rolling_evaluation.json", refs=["forecast_rmse", "rmse"], derivation=["计算 y-y_hat", "误差平方后求平均", "开平方恢复目标变量量纲"], applicability=["预测值和真实值按时间配对"], failure=["异常值会放大指标", "不同量纲不可直接比较"], test=["为什么 RMSE 会比 MAE 更受大误差影响？"], knowledge_id="rmse"),
        _card(data, card_id="prediction_interval", concept="预测区间与校准", category="uncertainty", formula_id="prediction_interval", artifact="rolling_evaluation.json", refs=["coverage", "interval_score"], derivation=["取得点预测", "估计预测误差尺度", "构造区间并在独立窗口检查覆盖率"], applicability=["存在独立校准窗口", "区间方法已声明"], failure=["未校准不能解释成概率", "OOD 时覆盖率可能失效"], test=["名义 95% 区间实际覆盖率是多少？"], knowledge_id="prediction_interval"),
        _card(data, card_id="cvar_metric", concept="CVaR 与尾部损失", category="risk", formula_id="cvar", artifact="tail_risk.json", refs=["cvar", "var"], derivation=["定义损失而非收益", "找到 alpha 分位点", "对超过分位点的损失求平均"], applicability=["损失定义和置信水平已声明", "尾部样本数足够"], failure=["尾部样本少", "分布漂移", "损失口径不一致"], test=["CVaR 与 VaR 有什么区别？"], knowledge_id="cvar"),
        _card(data, card_id="portfolio_variance", concept="组合方差和协方差", category="portfolio", formula_id="portfolio_variance", artifact="portfolio_robustness.json", refs=["portfolio_variance"], derivation=["读取权重", "读取协方差矩阵", "计算二次型并检查约束"], applicability=["权重和协方差可追溯", "solver status 可验证"], failure=["协方差估计不稳定", "相关性在压力期变化"], test=["为什么低相关资产可能降低组合风险？"], knowledge_id="portfolio_variance"),
        _card(data, card_id="data_quality_gate", concept="数据质量状态", category="data_quality", formula_id="status_gate", artifact="data_quality.json", refs=[], derivation=["检查日期、重复粒度、缺失和 PIT", "检查来源新鲜度与修订状态", "将结果传给研究门禁"], applicability=["质量报告已生成", "PIT 规则已声明"], failure=["availability_time 缺失", "重复 grain", "数据源冲突"], test=["为什么抓取时间不能替代历史可用时间？"], knowledge_id="point_in_time"),
        _card(data, card_id="causal_boundary", concept="预测贡献与因果边界", category="causality", formula_id=None, artifact="knowledge_explanations.json", refs=[], derivation=["读取模型贡献或统计关联", "区分 predictive 与 causal_hypothesis", "没有干预设计则标记 not_available"], applicability=["只用于解释模型如何使用变量"], failure=["混杂", "反向因果", "把相关性写成干预效果"], test=["特征贡献为什么不是因果效应？"], knowledge_id="contribution_vs_causality"),
    ]
    for card, claim in zip(cards, explanations or []):
        card["lesson"] = build_lesson(result=data, claim=claim)
    return {"schema_version": "1.0", "card_count": len(cards), "generated_from": ["analysis.json", "rolling_evaluation.json", "portfolio_robustness.json", "monitoring_status.json", "result_lineage.json"], "cards": cards}
