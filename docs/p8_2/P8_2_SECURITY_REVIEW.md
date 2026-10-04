# Finathink P8.2 Security Review

**Status:** preliminary local implementation review; final security gate
pending
**Date:** 2026-10-03 (Asia/Shanghai)

## Threat model

P8.2 introduces four new trust boundaries:

1. normalized data and event payloads entering the server/UI;
2. a same-origin JavaScript visualization bundle;
3. optional Qlib/vectorbt environments and adapter artifacts;
4. a possible QMT bridge on a local or trusted-LAN host.

The primary threats are fabricated or future-leaking data, XSS/DOM injection,
credential leakage, arbitrary code execution, unbounded resource use, raw
third-party object leakage, and accidental trading/account control.

## Controls implemented

| Threat | Current control | Evidence/state |
| --- | --- | --- |
| Unsafe contract payload | JSON-safe recursive normalization; rejects non-finite values, executable keys, sets, oversized payloads | `p8_2/contracts.py` focused tests pass |
| Invalid chart data | Schema/fingerprint/timestamp/finite-value/chronological checks; 10,000-point cap | `frontend/src/research.js` tests |
| HTML/inspector injection | Server interpolations use `html.escape`; frontend table cells use `textContent` | Route/frontend source inspection |
| Remote script supply chain | Same-origin static bundle; no CDN/remote font; asset allow-list | `/research` route and CSP tests |
| QMT credential leakage | Constructor/record credential-key rejection; token digest only; no broker password field | QMT tests/source inspection |
| Trading/account control | No order/cancel/account methods; explicit denied list; read-only status | QMT tests and route payload |
| Bridge exposure | Loopback default, trusted-LAN opt-in requires a token, bounded token/port/limit checks | `QMTBridgeClient` |
| Optional import failure | Capability detection catches absent/hostile metadata; adapters return fallback | Capability/adapter tests |
| Generated code execution | Contract key deny-list and no execution path in chart/ML UI | Source review; broader audit pending |
| Source/provenance loss | Dataset/point fingerprints, source mode, as-of/PIT and limitations travel in payload | Research route tests |

The repository secret scanner is now scoped to skip all isolated virtual
environments (`.venv*`) and has a regression test for the original
`.venv-vectorbt` false positive. The third-party Pillow file was not modified;
the scanner now reports a clean result on the project tree.

The shell CSP currently permits `script-src 'self'` to serve the local bundle.
It does not permit inline scripts, remote scripts, or arbitrary origins. The
final HTTP-header test must verify the same policy on every HTML route.

## QMT security boundary

Authentication remains in the official QMT client. Finathink may receive a
short-lived bridge token, but never a broker password or account credential.
The bridge must stay loopback/trusted-LAN, use explicit origin/host policy,
bound request sizes, and expose health/read-only market-data methods only.
Captured records must be scrubbed of credentials and vendor session objects
before persistence.

Real QMT is not installed or connected in this environment. The current
security evidence is therefore a mock/offline boundary, not a vendor-host
penetration test.

## Optional sandbox boundary

Qlib 0.9.7 is present only in the isolated `.venv-qlib-py312` smoke
environment (and was cross-checked in disposable Linux/amd64 Docker).
vectorbt 1.1.1 is present only in the isolated `.venv-vectorbt` smoke
environment; neither is a core dependency.
Each optional engine receives only approved normalized datasets and explicit
resource limits. Raw handlers, models, portfolios, credentials, arbitrary
network endpoints, and generated code cannot cross back into Finathink
contracts. License notices and dependency audits are security/release inputs,
not optional paperwork.

## Open findings / hardening items

| Priority | Finding | Required action |
| --- | --- | --- |
| P1 | Real QMT bridge security is unverified | Review supported-host auth, TLS/trusted-LAN policy, token rotation, logs, and firewall posture before connection |
| P1 | Browser-level XSS/CSP and dependency behavior are not tested in a real browser | Run an approved headless browser/DOM security smoke; retain no Computer Use |
| P1 | Optional package licenses and transitive advisories need final audit | Run frontend/npm and isolated Python audits; do not promote vectorbt without legal review |
| P2 | Real bridge method/field rejection and replay behavior remain vendor-unverified | Preserve case-insensitive denial, duplicate/order checks, and captured-fixture tests when a vendor bridge is reviewed |
| P2 | Bundle lifecycle cleanup and error telemetry need review | Dispose chart/resize listeners and avoid leaking payloads into logs |
| P2 | Generated educational code safety needs the full existing static scanner | Attach scanner output to final report |

## Current evidence

The full local Python suite and focused P8.2 tests pass, and the frontend suite
passes its four Node tests. `npm audit --audit-level=high`
reported zero vulnerabilities, the isolated vectorbt environment passed
`pip check`, and the secret scanner now reports
`secret scan passed (no known credential patterns)`. These are useful local
checks, not a final security sign-off. Full Python dependency audit,
clean-install, HTTP-header coverage across all routes, optional-sandbox audit,
and any real bridge/browser penetration checks must be recorded by the root
agent in `P8_2_FINAL_VALIDATION_REPORT.md`.
