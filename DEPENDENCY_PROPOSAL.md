# Dependency Proposal

## P4 decision

P4 adds no third-party dependency. The experiment engine uses the existing
Python standard library (json, hashlib, pathlib, tempfile) plus the already-
approved pandas/P3 APIs.

| Name | Version | Purpose | License | Maintenance | Security | Phase |
|---|---|---|---|---|---|---|
| None | N/A | No new capability requires installation | N/A | N/A | No new supply-chain surface | P4 |

Any future dependency requires a new proposal and review before installation.
