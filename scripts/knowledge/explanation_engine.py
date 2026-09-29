"""Build constrained explanations from already-computed artifact fields."""
from .formula_registry import get_formula


def build_explanations(data):
    forecast = data.get("forecast", {}) if isinstance(data.get("forecast"), dict) else {}
    model = str(forecast.get("model", ""))
    formula_id = "naive_last_value" if "naive" in model else "rolling_mean_forecast" if "rolling" in model else "historical_mean_forecast"
    explanations = [{"claim_id": "forecast_model_001", "title": "模型如何得到预测", "claim_level": "predictive", "claim_type": "model_definition", "statement": f'当前选择模型为 {model or "未提供"}；该说明描述预测关系，不等同于因果关系。', "formula": get_formula(formula_id), "evidence_refs": ["analysis.json", "rolling_evaluation.json"], "calculation_refs": data.get("forecast", {}).get("lineage_refs", []), "confidence": forecast.get("calibration_status", "not_available"), "caveats": ["未校准区间不能解释为覆盖概率", "状态变化可能使历史关系失效"], "next_check": "观察未来滚动窗口并更新校准状态"}]
    portfolio = data.get("portfolio_robustness")
    if isinstance(portfolio, dict):
        explanations.append({"claim_id": "portfolio_objective_001", "title": "组合为什么得到这些权重", "claim_level": "decision", "claim_type": "constraint_and_risk", "statement": f'权重来自 {portfolio.get("selected_covariance_model", "声明的协方差模型")} 的约束求解；绑定约束和 fallback 状态必须结合 solver 输出解释。', "formula": get_formula("portfolio_objective"), "evidence_refs": ["portfolio_robustness.json"], "calculation_refs": portfolio.get("calculation_refs", []), "confidence": portfolio.get("solver_status", "not_available"), "caveats": ["优化权重不是收益保证", "协方差估计和交易成本假设会改变解"], "next_check": "重新检查成本、协方差和约束敏感性"})
    explanations.append({"claim_id": "failure_boundary_001", "title": "什么时候预测会失效", "claim_level": "observed", "claim_type": "failure_boundary", "statement": "当数据新鲜度、PIT、校准、OOD 或约束状态不满足时，应降低结论等级或停止依赖分析。", "formula": {"formula_id": "status_gate", "tex": "", "alt_text": "状态门禁决定是否可以依赖结论", "variables": {}}, "evidence_refs": ["data_quality.json", "forecast_contract", "monitoring_status.json"], "calculation_refs": [], "confidence": "rule_based", "caveats": ["这是研究门禁，不是市场因果判断"], "next_check": "下一次数据刷新或模型验证"})
    return explanations
