# P7 Reproducibility Review

P7 payloads are canonical JSON, history links carry source fingerprints, and
strategy links retain P6.6 IR/feature/provenance references. The migration is
additive and can be applied to a disposable SQLite database; the same SQL is
portable to the PostgreSQL target with the existing migration gate.

The reproducibility gate reruns both Python environments, the focused P7 and
P6.6 contract tests, Ruff, notebook execution, governance, pip checks, and the
PostgreSQL migration check. A clean worktree and HEAD commit are recorded with
the final report so an auditor can distinguish code evidence from prose.
