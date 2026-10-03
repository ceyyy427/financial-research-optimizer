# P8 license and rights review

## Project material

Source code and project documentation are MIT under `LICENSE`, copyright 2026
Finahinking contributors. Contributions are accepted under the same license
unless a future contributor agreement says otherwise.

## Dependencies

The direct runtime/development dependencies (`numpy`, `pandas`, `pytest`,
`ruff`, `jupyterlab`, `ipykernel`, and pinned `setuptools`) are permissively
licensed (BSD/MIT) and recorded in `DEPENDENCY_RECORD.md` and
`requirements.lock`. Transitive licenses must be rechecked on every lock
refresh; an unclear, source-available, or GPL-only dependency is a release
block until reviewed.

## Data, fonts, and icons

Bundled fixtures are project-authored or captured from public official sources;
their source, capture purpose, and reuse basis are listed in
`docs/DATA_SOURCES.md`. Do not add proprietary datasets, unlicensed fonts,
icons, images, or copied knowledge. Knowledge entries require a source and a
reviewer; an AI draft is not an authoritative source.

## Release decision

The license review is complete for the current source tree. A maintainer must
re-run dependency and asset attribution checks before attaching a public binary
or publishing a GitHub release.
