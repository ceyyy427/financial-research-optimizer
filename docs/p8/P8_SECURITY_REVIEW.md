# P8 security review

| Boundary | Control/evidence | Result |
| --- | --- | --- |
| Secrets | Environment/config only; never log keys; secret scan in CI | Pass for bounded detector; expand patterns before hosted use |
| Network | Allowlisted providers, bounded timeout/retry/payload, captured replay | Pass for admitted fixture path |
| Local app | Loopback-only binding, exact loopback Origin/Host checks, protected forms, CSP, no broker/order endpoint | Pass for local boundary |
| User data | Local persistence; redacted diagnostics; no required telemetry | Pass for local boundary |
| Dependencies | Lock, `pip check`, and CI/release `pip-audit==2.10.1 -r requirements.lock --strict` | Local run: `No known vulnerabilities found` after upgrading the pinned setuptools build backend to 84.0.0 |
| Supply chain | PEP 517 build, pinned backend, artifact/checksum workflow | Review per release |
| Reporting | `SECURITY.md` private-report path and seven-day acknowledgement target | Pass |

The review does not claim a hosted threat model, binary notarization, or an
external penetration test. Real-money execution and cloud synchronization are
absent by construction.
