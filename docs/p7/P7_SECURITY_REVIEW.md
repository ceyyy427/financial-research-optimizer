# P7 Security Review

## Threats and controls

| Threat | Control | Evidence target |
| --- | --- | --- |
| Cross-user read | Session-to-owner check on every repository method | P7 privacy tests |
| SQL injection | Bound parameters; no dynamic identifiers | injection test + Ruff review |
| Consent bypass | `publish_projection` requires consent and current fingerprint | projection test |
| Data over-sharing | Field allow-list and sanitized payload | projection test |
| Stale public result | Fingerprint comparison marks `STALE` | stale-projection test |
| Prompt/tool injection | typed payloads; no executable content or tool dispatch | boundary review |
| Session abuse | active principal, expiry, revocation checks | auth tests |

No secrets or broker credentials are introduced. Community posts are untrusted
content; they are data, not instructions. The quant and research tool gateway
remains the authority for calculations, and P7 never executes arbitrary code.
Residual risk: production deployment still needs platform key management,
rate limits, abuse reporting, and a PostgreSQL operational backup/restore
exercise before any hosted release.
