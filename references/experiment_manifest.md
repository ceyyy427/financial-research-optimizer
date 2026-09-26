# Experiment manifest contract

`experiment_manifest.json` is the immutable run ledger. It binds the research configuration, data snapshot, code, environment, randomness, model/feature versions, windows, and produced files. A run is `complete` only when every required field is present and the listed output hashes can be checked.

## Required fields

| Field | Required content |
|---|---|
| `experiment_id` | Stable human-readable run identifier |
| `config_fingerprint` | Hash/fingerprint of the validated research config |
| `data_snapshot_hash` | Algorithm, digest, and snapshot path |
| `code_version` | Commit, repository, and dirty-worktree flag |
| `environment` | Python/Java/platform and dependency-lock identity |
| `random_seeds` | Every seed used by preprocessing, model fitting, and simulation |
| `model_parameters` | Frozen hyperparameters and optimizer parameters |
| `feature_version` | Feature schema/code version |
| `train_window` / `evaluation_window` | Date/row ranges and evaluation method |
| `outputs` | Every output path, kind, and SHA-256 digest |
| `reproducibility_status` | `complete`, `partial`, or `failed` |

Optional `source_reconciliation` records the conflict status, counts, canonical source, and whether dependent analysis was stopped. The HTML header and every decision-table row must expose the experiment ID and status.

Validate with:

```bash
python3 scripts/validate_experiment_manifest.py examples/experiment_manifest.json
```
