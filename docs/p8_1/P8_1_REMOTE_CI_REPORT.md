# P8.1 Remote CI Report

Recorded: 2026-10-03 (Asia/Shanghai)

Status: canonical CI exists and is green for canonical commit
`f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5`; there is no remote CI evidence for
the unrelated local P8.1 line.

## Canonical repository evidence

The public repository
[`ceyyy427/financial-research-optimizer`](https://github.com/ceyyy427/financial-research-optimizer)
has default branch `main`. At the audit point, `main` resolves to
`f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5` and contains these workflows:

- `.github/workflows/ci.yml` (`financial-research-optimizer-ci`)
- `.github/workflows/publish-package.yml` (`publish-python-package`)

The canonical CI workflow validates contracts and preflight behavior,
generates offline example artifacts, runs tests, and performs wheel clean-
install/CLI exercises on Python 3.11 and 3.12.

## Verified workflow runs

| Workflow | Run | Event / commit | Result | Verified jobs |
|---|---|---|---|---|
| `financial-research-optimizer-ci` | [36587291653](https://github.com/ceyyy427/financial-research-optimizer/actions/runs/36587291653) | push to `main` at `f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5` | completed / success | `test`, `clean install (3.11)`, and `clean install (3.12)` all succeeded |
| `publish-python-package` | [36587333322](https://github.com/ceyyy427/financial-research-optimizer/actions/runs/36587333322) | workflow dispatch at `f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5` | completed / success | distribution build/upload and GHCR container publication succeeded |

The first run was created at `2026-09-29T15:03:42Z` and completed at
`15:04:16Z`. The publish run was created at `15:04:01Z` and completed at
`15:04:49Z`.

The publish workflow includes a conditional PyPI step that exits successfully
when `PYPI_API_TOKEN` is absent. Therefore a green workflow is not evidence by
itself that a PyPI upload occurred; this report makes no PyPI publication
claim.

## Relationship to the local P8.1 work

The local comparison commit is
`e715b289a9f118858982045800694fefb129a7b2` plus uncommitted P8.1 changes at
this checkpoint. It has no merge base with canonical commit `f0cb4b6...`.
Consequently:

- the successful canonical CI run validates the canonical remote tree only;
- it does not validate the local shared shell, launch imagery, Quant/Strategy
  result refinements, local workflow files, or P8.1 documentation;
- the successful publish workflow does not make the local P8.1 tree a released
  artifact;
- no new remote workflow was triggered because no push or release mutation was
  performed.

## Gate result

| Gate | Result | Reason |
|---|---|---|
| Canonical repository has real CI | PASS | Workflow files and completed runs were verified through authenticated, read-only GitHub queries. |
| Canonical tip CI is green | PASS | Run `36587291653` succeeded at canonical `main` tip `f0cb4b6...`. |
| Local P8.1 commit has canonical CI | FAIL / NOT RUN | The local line is unrelated and has not been pushed. |
| `REMOTE_CI` for P8.1 public beta | **FAIL / CONDITIONAL** | Requires an approved history strategy, a reachable P8.1 commit on canonical GitHub, and a successful run tied to that exact commit. |

No local test result should be relabeled as GitHub Actions evidence. The final
validation report must keep `REMOTE_CI` conditional until an exact P8.1 remote
commit and its successful workflow URL are recorded.
