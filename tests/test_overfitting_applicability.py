from overfitting_applicability import assess_applicability


def test_diagnostics_are_triggered_by_inputs_not_unconditionally():
    result = assess_applicability(candidate_count=2, trial_count=1, observations=25, paired_loss=True, portfolio_returns=False)
    statuses = {item["method"]: item for item in result["methods"]}
    assert statuses["DM"]["applicable"] is True
    assert statuses["WRC"]["status"] == "not_applicable"
    assert statuses["SPA"]["status"] == "not_applicable"
    assert statuses["DSR"]["status"] == "not_applicable"
    assert statuses["PBO"]["status"] == "not_applicable"
    assert result["gate_status"] == "pending"
