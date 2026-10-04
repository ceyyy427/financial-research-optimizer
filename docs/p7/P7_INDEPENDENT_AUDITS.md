# P7 Independent Pass Register (A–J)

This register maps the mission's ten independent passes to executable evidence.
“PASS” is scoped to the local deterministic slice; hosted operational risks are
explicitly carried to `P8_READINESS_REPORT.md`.

| Pass | Required focus | Evidence | Result |
|---|---|---|---|
| A | Architecture | `P7_ARCHITECTURE.md`, migration 003, `tests/p7` | PASS |
| B | Personal data | owner-scoped nodes, export/deletion, `personal.py`, adversarial tests | PASS |
| C | Mastery | typed `MasteryEvidence`, explainable state, misconception correction tests | PASS |
| D | Personalization | bounded `context.py`, evidence-grounded optional guidance, truth boundary | PASS |
| E | Community | typed claims/attachments, room membership, summaries, event/strategy slices | PASS |
| F | Privacy | private-by-default schema, explicit consent, revocation, room scope | PASS |
| G | Security | session lifecycle, parameterized SQL, inert prompt/tool/link sanitizer | PASS |
| H | Research integrity | source fingerprints, limitations, feature/backtest/OOS/paper fields, P6.5 adapter | PASS |
| I | Learning integrity | explicit mastery outcomes, misconception lifecycle, timeline and question loop | PASS |
| J | Reproducibility | dual environments, Ruff, notebook, governance, pip, PostgreSQL, provenance | PASS |

The passes do not grant a production authorization. They certify that each
local contract has a named implementation and test; any unavailable hosted
control remains a readiness item rather than an invented capability.
