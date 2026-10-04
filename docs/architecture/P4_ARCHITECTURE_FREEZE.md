# P4 Architecture Freeze

**Status:** Frozen for human review

**Phase:** P4 Architecture Freeze

**Boundary:** P0–P4 are complete; P5 is design-only and awaits human approval.

## 1. ResearchRun domain model

`ResearchRun` is the durable research-memory object of Finahinking. It binds
the question that motivated an investigation to the evidence, computation, and
interpretation that followed it. The frozen P4 record contains:

| Object | P4 representation | Why it matters |
| --- | --- | --- |
| **Question** | Required research question text | States what the researcher wants to understand. |
| **Hypothesis** | Required hypothesis text | Makes the proposed explanation falsifiable or at least inspectable. |
| **Dataset** | Normalized dated records, columns, provenance, and dataset fingerprint | Identifies the observations used by the experiment. |
| **Factor** | Name, definition, explanation, limitations, and computation supplied by a P3 `FactorDefinition` | Makes the transformation interpretable instead of hiding it behind a metric. |
| **Method** | Explicit method name, currently `information_coefficient` | States how evidence was evaluated. |
| **Parameters** | Canonical JSON values such as horizon and factor shift | Exposes configuration and supports deterministic replay. |
| **Result** | Canonical JSON metrics plus result fingerprint | Preserves the measured evidence and detects resulting drift. |
| **Conclusion** | Required researcher-authored conclusion | Records what the researcher believes the result means. |
| **Insight** | Required researcher-authored insight | Captures reusable understanding for future research memory. |
| **Limitations** | Factor and experiment limitations | Prevents a number from being presented without assumptions or caveats. |

This is why `ResearchRun`, rather than `Factor`, is the core object: a factor
can be reused in many questions, datasets, methods, and interpretations. A run
preserves the complete chain and can later become a node in a personal research
graph without changing the P4 execution contract.

## 2. Experiment lifecycle

```text
Creation -> Configuration -> Execution -> Validation -> Result Storage -> Insight Generation
```

### Creation

The researcher provides a question, hypothesis, validated `Dataset`,
`FactorDefinition`, and an intended conclusion and insight. `ResearchRun.create`
rejects missing required narrative fields and captures a stable run identity.

### Configuration

`ExperimentEngine.execute` fixes the method and records parameters, including
the forward-return horizon and the one-period factor shift. The P4 engine does
not hide these choices in global state.

### Execution

The engine computes the documented factor over the dataset's close series,
constructs forward returns, and evaluates their information coefficient. It
does not call a broker, run stored code, or fetch data implicitly.

### Validation

Dataset schema and price constraints are checked before computation. Invalid
horizons, missing close prices, malformed records, and unsafe run IDs are
rejected; canonical serialization normalizes non-finite metrics explicitly.
Constant or insufficient series yield an explicit undefined metric rather than
a fabricated value.

### Result storage

The completed record is serialized as canonical JSON and can be written by
`RunStore` with a path-safe ID, a temporary file, `fsync`, and an atomic replace.
Loading revalidates the schema and fingerprints. Storage remains local in P4.

### Insight generation

P4 stores the researcher's conclusion and insight; it does not pretend to
generate financial advice or automatically infer knowledge. That explicit
human interpretation is the hand-off point to future research memory systems.

## 3. Data lineage model

```text
Dataset -> Factor -> Experiment -> Result
```

1. **Dataset:** P2 normalization and provenance identify provider, source URL,
   retrieval metadata, license, dated records, columns, and a fingerprint.
2. **Factor:** P3 supplies a named, defined, explained, limitation-bearing
   transformation. Its name and definition are carried into the run.
3. **Experiment:** P4 binds the dataset and factor to a method and parameters,
   while retaining the question and hypothesis that give the work meaning.
4. **Result:** the metric payload, conclusion, insight, limitations, creation
   time, engine version, and result fingerprint are stored together.

To answer “Where did this result come from?”, a reader starts at the result
fingerprint, follows the recorded method and parameters to the factor and
dataset fingerprints, then uses the dataset provenance to identify the source.
The current chain is strong for local replay; source release IDs, environment
versions, and factor implementation digests remain deferred improvements.

## 4. Fingerprint strategy

### Dataset fingerprint

The normalized dataset payload is converted to canonical JSON with sorted keys,
stable separators, normalized timestamps, and non-finite values represented
explicitly. SHA-256 of that payload is stored alongside the payload.

### Result fingerprint

The result fingerprint covers the dataset fingerprint, factor name and
definition, method, parameters, and result values. This makes a changed
configuration visible even when the final metric happens to look similar.

### Drift detection

- **Dataset changes:** reproduction compares the candidate dataset fingerprint
  with the recorded fingerprint and raises `ReproducibilityError` on mismatch.
- **Parameter changes:** the recorded parameters are included in the result
  fingerprint and are replayed. P4 does not accept a separate candidate
  parameter mapping, so explicit sensitivity comparison is a future requirement
  rather than a frozen API feature.
- **Result changes:** reproduction recomputes the experiment and compares the
  candidate result fingerprint with the recorded one.
- **Factor changes:** a changed factor name is rejected directly; a changed
  definition or computation is reflected through the result fingerprint. A
  source revision or implementation digest is not yet stored.

Fingerprints are integrity evidence, not proof that a conclusion is correct.
They show whether the recorded inputs and outputs are the same.

## 5. Storage decision

### Current choice: local JSON `RunStore`

Local JSON is acceptable for P4 because it is inspectable, portable, easy to
diff, deterministic, safe to validate without code execution, and sufficient
for one-researcher local workflows. Atomic writes and path-safe IDs protect the
small persistence boundary without introducing a database or service.

### Future migration considerations

- **PostgreSQL:** suitable when indexed queries, concurrent writers, migrations,
  and access control become real requirements. A migration must preserve the
  canonical payload and fingerprints, not silently reinterpret records.
- **Research Graph:** suitable when questions, evidence, results, and insights
  need explicit typed edges and cross-run traversal. The P4 record can remain a
  node payload; graph edges should be additive.
- **Knowledge Engine:** suitable when validated insights become reusable
  knowledge objects. It must distinguish observed evidence from derived claims
  and preserve provenance back to the run.

No migration is performed in P4.

## 6. Extension points

- **P5 — Backtest & Evaluation:** may add strategy intents, portfolio ledgers,
  positions, trades, orders, returns, risk, and performance attribution around
  the existing ResearchRun boundary. It must remain human-approved,
  timestamp-safe, and non-advisory.
- **P6 — Knowledge Engine:** may index ResearchRun conclusions and insights,
  introduce evidence/knowledge nodes, and expose provenance-aware retrieval.
  It must not erase uncertainty or turn descriptive research into advice.
- **P7 — Agent Evolution System:** may use governed research memory to improve
  agent planning and review. It remains outside the current architecture and
  requires its own safety, evaluation, and approval gates.

These are extension points, not implementation commitments. The P4 freeze is
valid only while the current boundary remains unchanged.
