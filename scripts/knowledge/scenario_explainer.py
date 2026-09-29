"""Render scenario explanations from saved scenario rows."""


def explain_scenarios(scenarios):
    return [{"scenario": item.get("scenario"), "status": item.get("status"), "interpretation": "模型计算的情景结果" if item.get("status") == "passed" else "情景不可用或已降级"} for item in scenarios or []]
