# Evolution Log

Record material architecture and governance changes here. Each entry should
state the date, change, reason, evidence, compatibility impact, and review
result. Small documentation corrections may be grouped in one entry.

## 2026-10-02 — P0 foundation

- Change: established repository governance, role contracts, and phase-gate
  records.
- Reason: make research changes auditable before adding data or factors.
- Evidence: `python scripts/validate_governance.py` and the governance tests.
- Compatibility: no package API or data format changes.
- Review: P0 gate recorded as PASS in `docs/PROJECT_STATE.md`.
