# Task 7 report — audited factor catalog admission

Implemented the audited factor catalog loader and the explicit human admission
boundary for registry writes.

## Implementation

- `factor_catalog.py` now enforces semantic versions and rejects duplicate
  source or required-field metadata while retaining deterministic fingerprints.
- `factor_catalog_loader.py` loads JSON catalogs, validates source/license/PIT/
  required fields/version/fingerprint metadata, rejects unknown future fields,
  duplicates and blocked entries, and exposes two audited built-in momentum
  entries.
- Missing admission returns a `CatalogAdmissionProposal` with
  `production_write=False`; only a matching `HumanAdmissionRecord` can call
  `FactorRegistry.register_catalog_entry`.
- Registry admission constructs paper-only metadata and health evidence and
  remains append-only.

## Verification

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_factor_catalog_loader.py tests/research/test_factor_catalog.py tests/research/test_factor_registry.py
27 passed

PYTHONPATH=src python3 -m pytest -q tests/research/test_factor_pipeline.py tests/research/test_factor_template_catalog.py
31 passed

python3 -m ruff check <Task 7 files>
All checks passed

PYTHONPATH=src python3 -m pytest -q
842 passed, 1 skipped, 1 failed
```

The full-suite failure is the pre-existing wheel-install integration test
`tests/validation/test_artifact_install.py::test_wheel_install_exposes_migrations_fixtures_and_local_routes`.
The focused catalog, registry, and factor-pipeline checks pass.

## Review fix round 1

Red regressions were added for swapped evaluation fingerprints, paper-only
selection, and source lineage. The registry now requires the catalog's
`evaluation_fingerprint` as well as its research fingerprint, preserves all
`source_ids` in `FactorMetadata`, and admits catalog entries as
`INSUFFICIENT_DATA` paper records that cannot be selected until separately
validated. Focused verification after the fix:

```text
PYTHONPATH=src python3 -m pytest -q tests/research/test_factor_catalog_loader.py
9 passed

PYTHONPATH=src python3 -m pytest -q tests/research/test_factor_catalog.py tests/research/test_factor_registry.py tests/research/test_factor_pipeline.py tests/research/test_factor_template_catalog.py
51 passed

PYTHONPATH=src python3 -m pytest -q
844 passed, 1 skipped, 1 failed
```

The same pre-existing wheel-install integration failure remains isolated to
`tests/validation/test_artifact_install.py`.

## Boundary

Catalog loading is read-only. Registry mutation requires a typed, explicit
human admission bound to the catalog research fingerprint; no live data,
execution, or trading behavior was added.
