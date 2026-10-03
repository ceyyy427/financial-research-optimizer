# P8 Readiness Report

P7.5 supplies a usable local product and a reproducible source-install path.
The repository is ready for the P8 public-beta release workflow, with the
following boundaries:

- Supported beta path: Python 3.11+ source install, SQLite, loopback, and
  captured BLS/sample journeys.
- Release engineering: CI, release workflow, license/security reviews,
  contribution contracts, issue forms, clean-install instructions, and secret
  scan are versioned under `.github/`, `scripts/`, `docs/p8/`, and root docs.
- Native macOS Apple Silicon packaging is not selected in this checkout because
  no signed/notarized artifact or Apple credentials are available; no binary is
  advertised.
- The repository has no configured Git remote, so no GitHub tag, release asset,
  or download URL is fabricated. A maintainer must run the workflow on a real
  remote before calling those P8 items complete.

P8 may begin directly with the public-beta checklist. It must stop after that
  gate and must not automatically begin cloud accounts, synchronization,
  broker execution, real-money workflows, or a major provider expansion.
