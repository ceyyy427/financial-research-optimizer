# P6 Hypothesis Contract

P6 distinguishes four kinds of statements:

| Kind | Owner | Evidence status |
| --- | --- | --- |
| `USER_CLAIM` | user wording | A claim to clarify or test |
| `SYSTEM_HYPOTHESIS` | planner | A proposed, falsifiable test |
| `EMPIRICAL_RESULT` | typed quant service | Observed normalized output |
| `INTERPRETATION` | explanation layer | Bounded reading of the result |

`Hypothesis` requires a question, claim, null hypothesis, universe, period,
factor or model, benchmark, evaluation boundary, and known assumptions and
limitations. It also carries a `hypothesis_id`, version, and fingerprint.

The planner must state the direction of the test and the metric that would
count as evidence. It must not silently change the user’s universe, dates,
factor definition, costs, benchmark, lag, or OOS boundary. A material change
creates a proposed revision and pauses at `HYPOTHESIS_PROPOSED` until the user
accepts it.

Hypotheses cannot contain Python, shell, import paths, callables, arbitrary
URLs, package requests, or unbounded search spaces. “Find the best strategy”
is rejected or narrowed to one pre-specified experiment; best-in-sample Sharpe
selection is prohibited by the P5.5 multiple-testing contract.
