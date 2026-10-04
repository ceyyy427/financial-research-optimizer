# P6 Evaluation Plan

Evaluation is fixture-driven and separates orchestration correctness from
quant calculation. The suite covers:

| Area | Required evidence |
| --- | --- |
| Classification | All eight categories, ambiguity, and stand-back boundaries |
| Hypothesis fidelity | User claim preserved; null, universe, dates, factor, benchmark, assumptions explicit |
| Planner | Typed spec, OOS boundary, frozen config, material-change confirmation, no grid search |
| Gateway | Allowlist, normalized responses, linkage, warning/limitation propagation, failure semantics |
| Primary workflow | Momentum question reaches evidence, explanation, card, and auditable learning state |
| Regression workflow | RegressionResult grounds beta/intercept/uncertainty and creates a card |
| Explanation | Required sections, no unsupported numeric or causal claim, undefined metrics retained |
| Learning | Card fields, prediction/reveal/explain, misconception and review updates |
| Security | Prompt injection and arbitrary execution attempts are rejected pre-dispatch |
| Reproducibility | Same fixture/config yields identical result and provenance fingerprints |

The tests use the existing deterministic P5/P5.5 fixtures and an isolated
statsmodels environment for regression. They do not install packages or call a
network. Each successful workflow records question, classification, hypothesis,
experiment, assumptions, tool calls, run IDs, artifacts, evidence refs,
explanation version, warnings, limitations, and learning events. Each rejected
workflow proves no evidence record was created.

Before the P6 Gate Review, run the focused P6 tests, the full pytest and ruff
gates, governance validation, both environment `pip check` commands, the P5
and P5.5 fixtures, forbidden-import scans, `git diff --check`, and a clean
worktree check. The final validation report must cite the actual command output
and the final provenance commit.
