"""Formula registry for teaching cards; formulas do not calculate results."""

FORMULAS = {
    "historical_mean_forecast": {"formula_id": "historical_mean_forecast", "tex": r"\hat{y}_{t+1}=\frac{1}{n}\sum_{i=1}^{n}y_{t-i+1}", "alt_text": "下一期预测值等于最近 n 个观测值的平均值", "variables": {"y": "目标变量", "n": "历史窗口长度"}},
    "naive_last_value": {"formula_id": "naive_last_value", "tex": r"\hat{y}_{t+1}=y_t", "alt_text": "下一期预测值等于当前观测值", "variables": {"y_t": "当前观测值"}},
    "rolling_mean_forecast": {"formula_id": "rolling_mean_forecast", "tex": r"\hat{y}_{t+1}^{(w)}=\frac{1}{w}\sum_{i=0}^{w-1}y_{t-i}", "alt_text": "下一期预测值等于窗口 w 内观测值的平均值", "variables": {"w": "滚动窗口长度"}},
    "portfolio_objective": {"formula_id": "portfolio_objective", "tex": r"\min_w\;w^{\mathsf T}\Sigma w-\lambda\mu^{\mathsf T}w+\gamma C(w,w_{t-1})", "alt_text": "在收益、协方差风险和换手成本之间优化资产权重", "variables": {"w": "资产权重", "Sigma": "协方差矩阵", "mu": "预期收益", "C": "交易成本"}},
}


def get_formula(formula_id):
    return dict(FORMULAS.get(formula_id, {"formula_id": formula_id, "tex": "", "alt_text": "公式不可用", "variables": {}}))
