# P6.6 Research Package Export

The exporter writes a bounded, path-safe research package containing:

```text
strategy.py          educational code
features.py          feature definitions and lineage
config.json          typed backtest/paper configuration
strategy_spec.json   reviewed StrategySpec and StrategyVersion
math_notes.md        code/math/finance traces
strategy_logic.md    readable signal and portfolio logic
research_report.json backtest, OOS, walk-forward, paper, comparison, drift
limitations.md       validity and security boundaries
provenance.json      fingerprints, commit, dependencies, run IDs
README.md            reproduction and scope instructions
tests/               deterministic package-level checks
```

The package fingerprint covers every emitted file and the provenance envelope.
Export rejects traversal, absolute paths, secrets, credentials, unsafe code,
and oversized payloads. It states that the artifact is for research and
education and is not a deployment or real-money trading package.
