# P6 Guided Quant Research & Learning — Execution Plan

## Scope and exit

P6 adds a Finahinking-owned, guided workflow around the frozen P5.5 quant
services. It answers bounded research questions, proposes one explicit
hypothesis and experiment, executes only after assumptions are accepted, and
returns evidence, explanation, and a small learning update. The phase ends at
the P6 Gate Review. P7 remains waiting for explicit human approval.

P6 does not add trading, brokerage, buy/sell recommendations, autonomous alpha
discovery, unrestricted strategy generation, hyperparameter sweeps, a swarm,
Community, or a general-purpose agent framework. It does not install a new
quant library or require MCP. P5.5 remains the calculation and validity
boundary.

The mission's authoritative P5 starting commit was
`358ade94bd26d246e907414fc3ac729dc5ae1d5e`. The checkout already contained
the approved P5.5 implementation, Gate A report, and P6 readiness decision
(`94b2863` and its predecessors) when this phase began; that delta is the
documented reason the live HEAD differed before P6 work continued.

## Work sequence

1. Freeze the domain models and state machine: `ResearchQuestion`,
   `Hypothesis`, `ExperimentSpecification`, assumptions, and the states from
   `QUESTION_RECEIVED` through `LEARNING_READY`.
2. Implement deterministic classification, hypothesis construction, and
   experiment planning. Material changes require an explicit confirmation
   token.
3. Route execution through the P5.5 typed gateway. The gateway allowlist is
   the only path to `quant.run_backtest`, `quant.run_regression`, performance,
   risk, benchmark, and inspection services.
4. Build the explanation and claim-grounding layer. Every quantitative claim
   points to a normalized result, evaluation report, or risk report and carries
   warnings and limitations.
5. Build learning cards, prediction/reveal/explain, misconception records, and
   the minimal auditable learning state.
6. Run the primary momentum workflow and the regression-learning workflow with
   deterministic fixtures, then run security, architecture, research-validity,
   explanation, learning, and reproducibility audits.
7. Update state and reports only after all P6 gate items and repository gates
   pass. Commit the final evidence and verify that its provenance commit is
   `HEAD`.

## Primary workflow

“Does momentum work in this dataset?” is classified as `QUANT`. The system
proposes the fixed cross-sectional lagged momentum slice, displays universe,
period, lag, costs, benchmark, OOS boundary, and limitations, waits for
assumption acceptance, calls the typed P5.5 service, and stores a linked
`ResearchRun`, `QuantRun`, `Artifact`, and evidence record. It then produces an
explanation and one learning card. A user may request a prediction before the
result and reveal it afterward; the prediction is stored as user input and is
never treated as evidence.

The second workflow, “How sensitive was this asset to the market?”, is also
`QUANT`. It uses the existing normalized statsmodels adapter through
`quant.run_regression`, explains beta, intercept, uncertainty, and limitations,
and creates a regression concept card. The adapter remains isolated in
`.venv-quant`.

The planner carries the P5.5 training/test boundary as explicit planned
metadata. The deterministic fixture vertical slice intentionally does not
claim a completed out-of-sample evaluation: its normalized provenance sets
`oos.is_oos=false` until a later-window dataset is supplied. Explanations retain
that limitation rather than infer OOS validity from the plan alone.

## Acceptance evidence

The implementation is accepted only when focused P6 tests and the complete
repository gates pass, both workflows produce reproducible linked records,
unsafe requests are rejected without side effects, and no quantitative claim
can be rendered without a source reference. The final report must record the
actual commands and commit; it must not infer success from documentation alone.
