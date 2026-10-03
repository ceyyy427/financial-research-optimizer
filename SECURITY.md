# Security Policy

Finahinking is a local-first research application. Please do not include
credentials, private datasets, brokerage details, or personal learning data in
public issues. Redact logs and diagnostic bundles before sharing.

## Supported versions

Security fixes target the latest `0.1.x` public-beta line and the default
branch. This project does not promise a hosted service or broker boundary.

## Reporting a vulnerability

For a suspected vulnerability, use a private GitHub Security Advisory for the
repository when available. If that channel is not yet enabled, contact the
maintainer privately through the repository owner and include a minimal
reproduction, affected commit/version, impact, and a safe contact method. Do
not open a public issue for an unpatched credential leak, code-execution flaw,
path traversal, or private-data disclosure.

We will acknowledge a report within seven days, triage severity and affected
scope, and publish a fix or mitigation note when it is safe to do so. Reports
about research methodology or knowledge correctness belong in the dedicated
issue templates, not as security vulnerabilities.

## Security boundaries

- API keys are read from process configuration and are never logged or stored
  in the learning graph.
- Network calls are allowlisted, bounded, and opt-in; sample mode uses local
  fixtures and works offline.
- User research and learning state remain local by default. Telemetry is not
  required and no private graph is uploaded by default.
- The app contains no broker SDK, order endpoint, real-money execution, or
  autonomous moderation path.
- Diagnostic exports must sanitize tokens, credentials, private research, and
  sensitive local paths.

See [PRIVACY.md](docs/PRIVACY.md), [P8 security review](docs/p8/P8_SECURITY_REVIEW.md),
and [Known Limitations](docs/KNOWN_LIMITATIONS.md) for the current threat and
capability boundaries.
