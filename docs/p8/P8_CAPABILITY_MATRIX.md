# P8 capability matrix

| Capability | Evidence in this checkout | Status |
| --- | --- | --- |
| Source install | `pyproject.toml`, `docs/INSTALLATION.md`, clean-install report | Ready |
| Offline sample mode | Captured BLS fixture and deterministic tests | Ready |
| Knowledge/quant/strategy journeys | P7.5 modules, tutorials, and full tests | Verify at P7.5 gate |
| Local persistence and migrations | SQLite default plus additive migration checks | Ready |
| CI | `.github/workflows/ci.yml` | Ready to run on a remote |
| Release workflow | `.github/workflows/release.yml` | Ready; requires maintainer tag |
| Security/secret checks | security review and CI scans | Ready to run |
| macOS Apple Silicon binary | No signed/notarized artifact in checkout | Not selected/conditional |
| GitHub release assets | No git remote or published release in checkout | External publish required |
| Website download links | Docs specify canonical GitHub release target | Pending real release URL |
| Cloud accounts/broker/real money | Deliberately absent | Out of scope |

## Independent P8 audits

- A Packaging — source install and artifact checks are defined; no binary is
  fabricated.
- B Documentation — README, tutorials, installation, limits, and contracts are
  present and cross-linked.
- C Licensing — MIT and fixture/third-party review are recorded.
- D Security — secret handling, bounded network, and reporting policy are
  documented.
- E Research Integrity — claims, provenance, OOS, paper, and no-advice
  boundaries remain explicit.
- F Knowledge Quality — typed concepts and reviewed-source rules are required.
- G Privacy — local state, outbound calls, telemetry, and backups are explicit.
- H Reproducibility — fixtures, lock, deterministic tests, and clean install
  are specified.
- I Contributor Experience — setup, tests, migrations, and issue templates are
  provided.
- J Clean Install — fresh-environment procedure is recorded and automated in
  CI.
