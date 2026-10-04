# P6 Experiment Planner

The planner transforms an accepted hypothesis into one bounded
`ExperimentSpecification`. The specification contains a registered tool name,
dataset and fingerprint, universe, factor/model, train/validation/test periods,
execution lag, costs, slippage, turnover treatment, benchmark, requested
metrics, validity profile, known limitations, and a frozen configuration
fingerprint.

Planning is a dry operation. It never imports a quant library, fits a model,
executes a command, or creates a result. The planner verifies that the
requested tool is in the P5.5 allowlist and that all required assumptions are
explicit. It rejects missing available-at semantics, overlapping OOS periods,
unbounded parameter sets, and a multiple-testing request without selection and
OOS metadata.

Material changes include universe expansion, date changes, factor definition,
benchmark, cost/slippage, parameter optimization, optional dependency, and
large experiment count. The planner returns `NEEDS_CONFIRMATION` with a
structured diff for these changes. It returns `REJECTED` for forbidden scope.

The resulting plan is immutable. A rerun with a different configuration gets a
new experiment and fingerprint, while the original plan and its assumptions
remain inspectable.

For the shipped fixture, `oos_design.status=planned` is deliberately distinct
from an executed OOS result. The momentum service records
`provenance.oos.is_oos=false`; a later test window must be supplied before an
explanation may describe the result as out of sample.
