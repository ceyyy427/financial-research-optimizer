# P4.5 Architecture Audit

**Result:** PASS

## Repository structure

Evidence was collected with `git ls-files`, `find`, `rg`, source inspection,
and the complete test suite.

| Boundary | Location | Responsibility |
| --- | --- | --- |
| Governance | root documents, `.agents/`, `scripts/validate_governance.py` | Project identity, role constraints, dependency policy, phase state, and gates. |
| Reality data | `src/finahinking/data/` | Provider isolation, provenance, normalized datasets, and validation. |
| Research features | `src/finahinking/features/` | Pure returns, volatility, momentum, drawdown, and correlation transforms. |
| Factor research | `src/finahinking/factors/` | Named factor definitions, limitations, alignment, IC, and coverage. |
| Experiment domain | `src/finahinking/experiments/` | ResearchRun modeling, deterministic execution/reproduction, and local storage. |
| Verification | `tests/`, `fixtures/`, `notebooks/` | Offline fixtures, unit/integration tests, and deterministic notebook execution. |
| Architecture memory | `docs/architecture/`, `docs/phases/`, `docs/reviews/`, `docs/superpowers/` | Frozen decisions, gates, independent reviews, plans, and specifications. |

The dependency direction remains one-way:

```text
provider -> dataset/provenance -> validation -> features -> factors
         -> ExperimentEngine -> ResearchRun -> RunStore
```

Providers are the only intended network boundary. Features are pure
transformations. Factors carry meaning and limitations. Experiments bind those
objects to questions, hypotheses, results, conclusions, and insights. Storage
operates on serialized records and does not execute them.

## Domain boundaries

- `Dataset` owns normalized observations and immutable provenance.
- `FactorDefinition` owns factor identity, explanation, limitations, and
  computation.
- `ExperimentEngine` owns the single P4 evaluation workflow.
- `ResearchRun` owns durable research memory and integrity fingerprints.
- `RunStore` owns path-safe local persistence and atomic replacement.

No brokerage, portfolio, backtest, knowledge-graph, agent, or model-serving
module exists in the source tree.

## Documentation structure

Phase gate designs/reviews, architecture freezes, dependency decisions, and
completion reports are separated by purpose. `docs/PROJECT_STATE.md` remains
the authoritative state record. P4.5 adds audit evidence without rewriting the
frozen P4 design.

## Extension points

- P5 can add backtest evidence around ResearchRun through versioned additive
  schemas and adapters.
- P6 can reference run IDs/fingerprints from a Personal Research Graph.
- P7 can expose capability-limited Data, Experiment, Knowledge, and
  Visualization tools without placing agent behavior inside the domain model.

These extension points are documented contracts, not implemented components.

## Correctness, maintainability, security, and research validity

- Small modules and dataclasses make boundaries understandable and testable.
- Dataset checks reject empty, invalid, duplicate, or unordered observations.
- ECB access constrains currency syntax, timeout, response schema, and redirect
  host.
- RunStore constrains run IDs and uses canonical JSON plus atomic writes; it
  does not use pickle or stored code.
- Research limitations and the no-advice boundary are carried with results.

## Findings

No Critical or Important architecture issue was found. Known non-blocking
limitations remain: local-only storage, permissive type checking when loading
some ResearchRun fields, no explicit schema-migration machinery beyond
`schema_version`, and no first-class evidence graph. These are recorded future
requirements and do not destabilize the P4 local research foundation.

## Pass decision

The architecture supports future P5/P6/P7 expansion through additive,
versioned boundaries while keeping the P4 research loop intact. **PASS.**
