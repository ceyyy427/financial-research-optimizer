# P8 release plan

P8 exposes the local-first research product as a conservative `0.x.y` open
source beta. It does not add cloud accounts, broker integration, real-money
execution, or required telemetry.

## Release sequence

1. Freeze the P7.5 product gate and record its commit.
2. Run tests, Ruff, notebook/governance, dependency, migration, secret, and
   provenance checks on a clean checkout.
3. Run the source clean-install smoke with sample mode and no network.
4. Build a source artifact and checksum; run the release workflow on a
   maintainer-owned tag `v0.x.y`.
5. Review license/rights, security, privacy, limitations, and contribution
   docs.
6. Publish the GitHub release only after the workflow succeeds; website links
   must point to the real release page/assets.

The repository contains the workflow and checks but does not claim a GitHub
release or create a tag without the maintainer's external publication step.

## Versioning and rollback

Use SemVer-compatible `0.x.y`: patch for fixes/docs, minor for additive beta
features, and never silently change a persisted schema. Additive migrations
must be tested from a fresh database and an upgraded user database. Preserve
the previous source artifact and user database backup for rollback.
