"""Read-only factor attribution helpers for precomputed contribution artifacts."""


def explain_contributions(contributions):
    return [{"factor": str(key), "contribution": value} for key, value in (contributions or {}).items()]
