# P8 security review

| Boundary | Control/evidence | Result |
| --- | --- | --- |
| Secrets | Environment/config only; never log keys; secret scan in CI | Pass by design |
| Network | Allowlisted providers, bounded timeout/retry/payload, captured replay | Pass by design |
| Local app | Loopback default; no broker/order endpoint | Pass by design |
| User data | Local persistence; sanitized diagnostic guidance; no required telemetry | Pass by design |
| Dependencies | Lock and `pip check`; CI vulnerability job is non-blocking only for unavailable advisory service and must report it | Review per release |
| Supply chain | PEP 517 build, pinned backend, artifact/checksum workflow | Review per release |
| Reporting | `SECURITY.md` private-report path and seven-day acknowledgement target | Pass |

The review does not claim a hosted threat model, binary notarization, or an
external penetration test. Real-money execution and cloud synchronization are
absent by construction.
