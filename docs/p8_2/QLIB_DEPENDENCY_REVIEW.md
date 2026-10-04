# Qlib Dependency Review

**Classification:** C — optional research sandbox
**Review date:** 2026-10-03 (Asia/Shanghai)
**Decision:** Linux/amd64 installation and a bounded import/LightGBM OOS smoke
succeeded; native admission and Qlib provider initialization remain deferred

## Executive decision

Do not install Qlib into Finathink's core `.venv` or `.venv-quant`. The native
host has Python 3.13.7, no `python3.12`, and no importable `qlib` package. A
separate native macOS arm64 Python 3.12 environment (`.venv-qlib-py312`)
successfully installed `pyqlib==0.9.7`, passed `pip check`, and passed a
six-row in-memory Qlib `LGBModel` smoke. A Linux/amd64 Docker check produced
the same model result. The smoke proves import/version compatibility,
LightGBM train/validation/OOS execution, and scalar-only result extraction in
an isolated environment. It does not prove Qlib provider initialization, real
data handling, or licensing of an external dataset.

The core `QlibResearchAdapter` therefore continues to return the transparent
Finathink deterministic baseline with `NOT INSTALLED`/`FALLBACK` state. Raw
Qlib objects are forbidden from crossing the adapter boundary.

## Environment evidence

| Environment | Python/platform | Qlib state | What the evidence proves |
| --- | --- | --- | --- |
| Core `.venv` | Python 3.13.7, macOS arm64 | `qlib` absent | Core starts/tests without Qlib; native Qlib compatibility is not established |
| Quant `.venv-quant` | Python 3.13.7, macOS arm64 | `qlib` absent | Existing quant environment remains unchanged |
| Native host | macOS arm64, Python 3.12.15 | `.venv-qlib-py312`; `pyqlib==0.9.7`; `pip check` PASS | In-memory Qlib `LGBModel` train/validation/OOS path works; provider remains uninitialized |
| Docker cross-check | Linux/amd64, Python 3.12 | `pyqlib==0.9.7`; import/training smoke PASS | Same bounded model path works under the alternate architecture; provider remains uninitialized |

LightGBM 4.7.0 is importable in the current core `.venv`, but it is not a Qlib
environment and does not prove that Qlib's workflow works. LightGBM is absent
from `.venv-quant`. No existing environment may be repurposed as the Qlib
sandbox merely because one transitive model package is present.

## Upstream package and compatibility facts

The reviewed upstream distribution is `pyqlib` 0.9.7 under the MIT license.
Its metadata declares Python `>=3.8`, while the published classifiers audited
for this phase list Python through 3.12. The moving upstream `main` branch and
the 0.9.7 release are different reproducibility targets; any functional spike
must keep the exact release/image/digest in its environment record.

The audited dependency surface includes NumPy, pandas, `mlflow<3.13`, Redis,
`dill`, `fire`, `ruamel.yaml`, `python-redis-lock`, `tqdm`, `pymongo`,
`loguru`, LightGBM, Gym, CVXPY, joblib, Matplotlib, Jupyter, nbconvert,
PyArrow, pydantic-settings, and `setuptools-scm`. Optional groups add RL,
analysis, client, docs, and test dependencies. This is materially larger than
Finathink core and is the reason Qlib stays isolated.

Native/macOS risks include OpenMP/LightGBM runtime requirements and platform
headers. Qlib also needs an initialized provider dataset before a meaningful
workflow can run. The installation spike did not authorize an external data
download or establish PIT/revision correctness.

## Isolated spike interpretation

The Linux/amd64 Docker result is recorded as:

```text
pyqlib 0.9.7 installation: PASS (native macOS arm64 Python 3.12.15)
Qlib import/version smoke: PASS (`qlib 0.9.7`, `lightgbm 4.7.0`)
Qlib initialization: NOT VERIFIED
Licensed sample dataset: NOT VERIFIED
LightGBM train/validation/OOS: PASS on in-memory fixture (`train=4`, `test=2`, OOS MAE `2.3976224998633064`)
Result normalization/no-object-leak test: PASS for smoke output (`raw_objects_returned=false`)
Core fallback without Docker: PASS BY EXISTING TESTS
```

The smoke is intentionally limited: it uses an in-memory DatasetH-shaped
fixture and does not call `qlib.init()` or download provider data. The result
must therefore be summarized as “isolated Qlib model smoke passed,” not “Qlib
is admitted.” The core adapter remains a deterministic fallback until a
reviewed provider/PIT fixture and native deployment decision exist.

## Finathink adapter contract

The only allowed input is a Finathink-owned `DatasetSnapshot` plus an
`MLResearchSpecification` containing dataset/feature fingerprints, explicit
train/validation/test periods, target, allow-listed model configuration, and
resource limits. The only allowed output is `MLResearchResult` containing:

- specification and dataset fingerprints;
- engine/model/environment identity;
- train/validation/OOS metrics and prediction artifact metadata;
- feature importance or an explicit unavailable state;
- uncertainty, warnings, and limitations;
- fallback status.

Qlib handlers, datasets, records, models, MLflow objects, or provider paths do
not become `ResearchRun`, `QuantRun`, UI payloads, or persistence objects.
Generated/model code is never executed from user text.

## Functional admission gate

Before Qlib can move beyond install-only evidence, the isolated Docker/sandbox
must pass all of the following with a small, licensed, offline fixture:

1. import and exact-version smoke;
2. Qlib initialization without an uncontrolled data download;
3. dataset handler and feature/target construction with PIT evidence;
4. one understandable LightGBM train/validation/OOS workflow;
5. normalized prediction, metric, importance, and limitation records;
6. deterministic artifact/environment fingerprints;
7. proof that no Qlib object leaks into core/JSON/UI;
8. `pip check`, dependency/advisory/license review, and resource bounds;
9. full core test and clean-install pass with Qlib absent.

Until these pass, the ML Lab must say `NOT INSTALLED` or `FALLBACK` and show
the deterministic Finathink baseline rather than a Qlib result.

## Secret-scan gate issue and resolution

Creating the isolated `.venv-vectorbt` initially exposed a repository-tooling
problem. The scanner traversed
`.venv-vectorbt/lib/python3.13/site-packages/PIL/ImageFont.py` and matched the
AWS-key-shaped test/string pattern `AKIA[0-9A-Z]{16}`. This was a third-party
Pillow file inside a gitignored virtual environment, not a Finathink source
secret.

The gate is now **PASS** after the scanner scope was corrected to skip path
parts beginning with `.venv` (while retaining the existing `.git`,
`__pycache__`, and `node_modules` exclusions). A regression test creates the
sentinel at runtime under `.venv-vectorbt` and verifies that isolated virtual
environments are not candidates. The dependency file was not edited and no
credential was found in project source.

Evidence captured after the fix:

```text
./.venv/bin/python scripts/secret_scan.py
secret scan passed (no known credential patterns)
./.venv/bin/python -m pytest -q tests/validation/test_secret_scan.py
1 passed
```

The same path-scope rule applies before a `.venv-qlib-py312` or `.venv-qmt` is
created, so optional dependency files cannot make the release gate
non-reproducible.

## Final status

```text
Native Python 3.12: AVAILABLE (`3.12.15`)
Native isolated Qlib: INSTALLED / SMOKE PASS
Linux/amd64 pyqlib 0.9.7 cross-check: PASS
Qlib functional/import/training smoke: PASS (isolated in-memory native + Docker smoke)
Qlib provider initialization/PIT dataset: NOT VERIFIED
Finathink deterministic fallback: AVAILABLE
Raw Qlib objects across boundary: FORBIDDEN
Core dependency admission: DEFERRED
Secret scan after isolated vectorbt env: PASS (historical Pillow false positive resolved)
```
