# P4.5 Data Provenance Audit

**Result:** PASS with documented future-strengthening requirements

## Traceability chain

```text
Source -> Dataset -> Dataset Version -> Factor -> Experiment -> Result -> Insight
```

| Link | Current evidence | Assessment |
| --- | --- | --- |
| Source | Provider name, source URL, retrieval timestamp when fetched live, and license text. | Traceable; fixture retrieval time may be absent by design. |
| Dataset | Normalized columns and dated records stored in the run. | Complete local snapshot. |
| Dataset Version | SHA-256 fingerprint of the canonical payload. | Strong content version; not an upstream provider release ID. |
| Factor | Name, definition, explanation, and limitations. | Interpretable; no source-code revision/digest. |
| Experiment | Question, hypothesis, method, parameters, creation time, and engine version. | Reconstructable for the P4 engine. |
| Result | Metric payload and SHA-256 result fingerprint. | Integrity-protected descriptive evidence. |
| Insight | Conclusion, insight, and limitations stored beside the evidence. | Human-authored and traceable. |

## Fingerprints

The dataset fingerprint covers records, columns, and provenance. The result
fingerprint covers dataset fingerprint, factor name/definition, method,
parameters, and result. Both use canonical JSON and SHA-256.

## Drift detection

- Dataset-content or provenance changes produce a dataset mismatch.
- Factor name changes are rejected directly.
- Factor definition, method, recorded parameter, or result changes alter the
  result fingerprint.
- Reproduction replays recorded parameters and detects a changed recomputed
  result; it does not compare an independently supplied candidate parameter map.
- Stored-payload tampering is detected at load time.

## Metadata preservation

Provider, URL, retrieval time, license, records, factor documentation, method,
parameters, result, timestamps, engine version, conclusion, insight, and
limitations survive JSON round-trip and local storage.

## Pass question

Can the system answer “Where did this result come from?”

**Yes for the frozen local P4 workflow.** A reader can traverse from the result
fingerprint to method/parameters, factor metadata, dataset fingerprint, stored
observations, and provider provenance. Cross-machine forensic reconstruction is
weaker because environment versions, an immutable upstream release/snapshot,
validation report, and factor implementation digest are not yet stored.

## Recommendation

Keep P4 frozen. Before a graph, remote store, or backtest is approved, implement
the already-documented versioned provenance envelope and migration tests. These
are P5/P6 readiness requirements, not a current P4 gate failure.
