# P6 Architecture

P6 is a guided, human-controlled workflow: the user remains in control of
material assumptions and the system never becomes an autonomous trader.

P6 is a small application layer above the frozen P5.5 quant platform.

```text
user question
  -> classifier
  -> hypothesis + experiment planner
  -> assumption review / human confirmation
  -> Finahinking typed tool gateway
  -> P5.5 service and normalized evidence
  -> claim grounding + explanation
  -> learning card + auditable learning state
```

The `p6` package owns orchestration, schemas, policy, explanation, and
learning. It does not own price calculations, regression fitting, portfolio
construction, or risk formulas. Those remain in `finahinking.quant` and are
reachable only through the approved typed gateway.

## State machine

The only forward execution states are:

`QUESTION_RECEIVED → CLASSIFIED → HYPOTHESIS_PROPOSED → EXPERIMENT_PROPOSED
→ ASSUMPTIONS_ACCEPTED → TOOL_EXECUTED → EVIDENCE_READY → EXPLANATION_READY
→ LEARNING_READY`.

Rejected, unsupported, failed, and cancelled outcomes are terminal records with
the reason and no fabricated evidence. A transition records timestamp, actor,
input fingerprint, and the preceding state. State transitions cannot
execute tools or mutate historical runs by themselves.

`GuidedResearchError` carries the terminal audit for a failed typed call, so a
caller can inspect the rejection without receiving a partial evidence bundle.

## Ownership and data flow

`ResearchQuestion` owns user wording and classification. `Hypothesis` owns the
claim, null, factor, universe, period, benchmark, and assumptions.
`ExperimentSpecification` is an immutable typed request. `AssumptionReview`
records accepted, rejected, and material-change decisions. `ToolRequest` and
`ToolResponse` mirror the P5.5 API envelope. `EvidenceBundle` contains only
normalized records and source fingerprints. `Explanation` references the
bundle; it never recomputes metrics. `LearningCard` and `LearningState` refer
back to the explanation and evidence.

All records are JSON-safe, bounded, content-addressed where applicable, and
append-only. Prompt text, imported documents, and stored evidence are data, not
instructions or policy.

## Extension boundary

An MCP wrapper may translate an external call into the exact gateway request,
but MCP is optional and cannot bypass validation. Adding an adapter, tool,
universe, optimization method, or execution connector requires a new reviewed
contract and does not happen as a side effect of a question.
