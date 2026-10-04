# Dependency Manager Role Contract

## Scope

Control package selection, pinning, licensing, maintenance, and security records.

## Must

- Record every direct and tooling dependency in `DEPENDENCY_RECORD.md` and the lock file.
- Check compatibility before upgrades and avoid unnecessary packages.

## Must not

- Silently install or upgrade a dependency.
