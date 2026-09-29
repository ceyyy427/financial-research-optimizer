"""Formula registry for teaching cards; formulas do not calculate results."""

FORMULAS = {
    "historical_mean_forecast": {"formula_id": "historical_mean_forecast", "tex": r"\hat{y}_{t+1}=\frac{1}{n}\sum_{i=1}^{n}y_{t-i+1}", "alt_text": "下一期预测值等于历史窗口观测值的平均值", "variables": {"y": "目标变量", "n": "历史窗口长度"}, "source_knowledge_id": "rolling_mean"},
    "naive_last_value": {"formula_id": "naive_last_value", "tex": r"\hat{y}_{t+1}=y_t", "alt_text": "下一期预测值等于当前观测值", "variables": {"y_t": "当前观测值"}, "source_knowledge_id": "naive_forecast"},
    "rolling_mean_forecast": {"formula_id": "rolling_mean_forecast", "tex": r"\hat{y}_{t+1}^{(w)}=\frac{1}{w}\sum_{i=0}^{w-1}y_{t-i}", "alt_text": "下一期预测值等于窗口 w 内观测值的平均值", "variables": {"w": "滚动窗口长度", "y": "目标变量"}, "source_knowledge_id": "rolling_mean"},
    "rmse": {"formula_id": "rmse", "tex": r"\operatorname{RMSE}=\sqrt{\frac{1}{T}\sum_{t=1}^{T}(y_t-\hat y_t)^2}", "alt_text": "预测误差平方平均值的平方根", "variables": {"y_t": "真实值", "yhat_t": "预测值", "T": "评估期数"}, "source_knowledge_id": "rmse"},
    "mae": {"formula_id": "mae", "tex": r"\operatorname{MAE}=\frac{1}{T}\sum_{t=1}^{T}|y_t-\hat y_t|", "alt_text": "预测误差绝对值的平均值", "variables": {"y_t": "真实值", "yhat_t": "预测值", "T": "评估期数"}, "source_knowledge_id": "mae"},
    "prediction_interval": {"formula_id": "prediction_interval", "tex": r"[\hat y-h_{1-\alpha/2},\hat y+h_{1-\alpha/2}]", "alt_text": "点预测加减预测误差边界形成的预测区间", "variables": {"yhat": "点预测", "h": "误差边界", "alpha": "尾部概率"}, "source_knowledge_id": "prediction_interval"},
    "calibration_coverage": {"formula_id": "calibration_coverage", "tex": r"\widehat{Coverage}=T^{-1}\sum_t1\{y_t\in I_t\}", "alt_text": "实际观测落入预测区间的比例", "variables": {"I_t": "第 t 期预测区间", "T": "评估期数"}, "source_knowledge_id": "calibration"},
    "portfolio_variance": {"formula_id": "portfolio_variance", "tex": r"\sigma_p^2=w^{\mathsf T}\Sigma w", "alt_text": "组合权重和协方差矩阵决定的组合方差", "variables": {"w": "资产权重", "Sigma": "协方差矩阵"}, "source_knowledge_id": "portfolio_variance"},
    "cvar": {"formula_id": "cvar", "tex": r"\operatorname{CVaR}_{\alpha}=E[L\mid L\geq VaR_{\alpha}]", "alt_text": "超过 VaR 分位点的尾部平均损失", "variables": {"L": "损失", "alpha": "置信水平", "VaR": "分位点损失"}, "source_knowledge_id": "cvar"},
    "portfolio_objective": {"formula_id": "portfolio_objective", "tex": r"\min_w\;w^{\mathsf T}\Sigma w-\lambda\mu^{\mathsf T}w+\gamma C(w,w_{t-1})", "alt_text": "在收益、协方差风险和换手成本之间优化资产权重", "variables": {"w": "资产权重", "Sigma": "协方差矩阵", "mu": "预期收益", "C": "交易成本"}, "source_knowledge_id": "portfolio_variance"},
    "status_gate": {"formula_id": "status_gate", "tex": r"\text{usable}=\text{PIT}\land\text{fresh}\land\text{calibrated}\land\neg\text{OOD}", "alt_text": "数据、校准和分布状态共同决定结论是否可依赖", "variables": {"PIT": "point-in-time 状态", "fresh": "新鲜度", "OOD": "分布外状态"}, "source_knowledge_id": "ood_detection"},
}


def get_formula(formula_id):
    return dict(FORMULAS.get(formula_id, {"formula_id": formula_id, "tex": "", "alt_text": "公式不可用", "variables": {}}))
