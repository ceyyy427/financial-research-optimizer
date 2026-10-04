# P8.1 Release Report

Recorded: 2026-10-03 (Asia/Shanghai)

Status: local beta candidate in validation; no canonical GitHub release or
hosted Finathink beta has been published from the P8.1 tree.

## Release identities must remain separate

There are two real but unrelated release lines at this checkpoint:

| Line | Identity | What is verified | What is not implied |
|---|---|---|---|
| Local Finathink line | local tag `v0.1.0` at baseline commit `e715b289a9f118858982045800694fefb129a7b2`, followed by uncommitted P8.1 work | prior local product/release history and recorded local test results | no canonical publication, no remote CI for P8.1, no GitHub P8.1 release |
| Canonical GitHub line | remote `main` and peeled `v1.3.0` at `f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5` | public repository, successful CI, successful publish workflow, published `v1.3.0` assets | no validation of the unrelated local Finathink P8.1 tree |

The existing GitHub release is
[`v1.3.0 — Explainable Forecasting Knowledge System`](https://github.com/ceyyy427/finathink/releases/tag/v1.3.0).
It is published, not a draft or prerelease, and exposes:

- `financial_research_optimizer-1.3.0-py3-none-any.whl` — 236,634 bytes,
  SHA-256 `398d5eb4d84ce41417842f75cb31985e24a788978698cfbf6da10e398c683828`
- `financial_research_optimizer-1.3.0.tar.gz` — 223,645 bytes,
  SHA-256 `61671077ebcf8b29b30c950e081a21923492500391ceb66d77c499b52106d2bc`

These are genuine remote artifacts, but they must not be presented as the
P8.1 Finathink release.

## Local P8.1 candidate contents

The local candidate includes the shared product shell, question-led journeys,
evidence inspector, eight-level knowledge path, Quant and Strategy result
surfaces, private Workspace continuity, static-site refresh, two packaged
launch images, finite gradient/crossfade motion, reduced-motion handling, tests,
and the P8.1 report set.

The most recent recorded full runs before the final result-view refinement
were `276 passed, 1 skipped` in `.venv` and `276 passed, 1 skipped` in
`.venv-quant`. A final candidate must still repeat the complete gate set after
all source and documentation edits; these earlier numbers are not a release
stamp for the final tree.

## Required local release evidence

Before a P8.1 artifact is called locally releasable, the final report must tie
all evidence to one committed tree and record:

1. full default and quant test suites;
2. Ruff and whitespace checks;
3. governance, secret, dependency, and package metadata checks;
4. notebook execution and database migration gates applicable to the tree;
5. wheel/sdist creation, checksums, and clean installation from the wheel;
6. real loopback HTTP journeys for critical routes and CSRF-protected writes;
7. a clean worktree after committing the validated candidate.

If any check is skipped because a service is unavailable, it must be marked as
deferred or failed with the exact reason; it cannot be silently treated as a
pass.

## Remote publication decision

No new tag, GitHub release, release asset, container, or hosted website was
created for P8.1. The local and canonical lines have no shared ancestor, so a
normal push to canonical `main` cannot establish the product release. The
history strategy in `P8_1_HISTORY_RECONCILIATION.md` requires explicit human
review before remote publication.

The static `site/index.html` is a local marketing artifact. Its canonical
repository link is real, but there is no verified deployment at
`finathink.cloud`; the existence of local HTML is not deployment evidence.

## Platform boundary

P8.1 does not require Apple Developer signing, notarization, or a signed DMG.
Those fields remain intentionally deferred rather than failed:

- `MACOS_SIGNING: DEFERRED`
- `MACOS_NOTARIZATION: DEFERRED`

## Release status

| Status field | Result at this checkpoint |
|---|---|
| `LOCAL_RELEASE` | CONDITIONAL — implementation exists; final post-edit gates, artifact build, commit, and clean-tree evidence remain |
| `CANONICAL_GITHUB` | PASS for repository identity and reachability; FAIL for hosting the local P8.1 line |
| `REMOTE_HISTORY_RECONCILIATION` | FAIL — unrelated histories require a human-reviewed strategy |
| `REMOTE_CI` | FAIL / NOT RUN for the P8.1 tree |
| `GITHUB_RELEASE` | FAIL / NOT CREATED for P8.1; existing `v1.3.0` belongs to the unrelated canonical line |
| `FINATHINK_CLOUD` | FAIL / NOT VERIFIED |
| `MACOS_SIGNING` | DEFERRED |
| `MACOS_NOTARIZATION` | DEFERRED |
| `PUBLIC_BETA` | **NOT RELEASED** |

Public beta can become true only when the selected canonical history contains
the exact validated P8.1 commit, its remote CI is green, its release assets are
traceable to that commit, and any claimed hosted URL has been independently
verified.
