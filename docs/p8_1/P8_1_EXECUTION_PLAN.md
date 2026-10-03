# Finathink P8.1 Execution Plan

Status: conditional final validation (baseline and local gates recorded
2026-10-03, Asia/Shanghai)

P8.1 has two coupled workstreams: make the local product understandable and
reproducible, then reconcile the validated mainline with the canonical GitHub
repository and publish a truthful public beta status.

## Sequence

1. Record the actual repository, tool, capability, security, and product
   baseline before substantive changes.
2. Audit the existing server-rendered shell, information architecture, design
   primitives, accessibility, performance, and real user journeys.
3. Write the design-system and information-architecture decisions, then add
   focused tests for each behavior that will change.
4. Implement a shared shell and page-level journeys without introducing a new
   frontend framework or arbitrary execution surface.
5. Exercise the event, knowledge, quant, strategy, paper, comparison, and
   continuity journeys through the real local HTTP server; retain parser and
   loopback smoke evidence for representative screens and mutations.
6. Re-run security, dependency, migration, notebook, packaging, clean-install,
   and full test gates. The current candidate has green runtime, lint,
   notebook, dependency, migration, secret, packaging, test, and governance
   checks; the remaining local-release failure is the dirty worktree at the
   time of capture.
7. Inspect the canonical remote, classify ancestry, preserve safety refs, and
   reconcile using normal Git operations only. The comparison is CASE D
   (`UNRELATED_HISTORY`), so this step remains a human-reviewed decision.
8. Push only after the local gates and worktree-clean preconditions pass; then
   inspect actual GitHub Actions and create a release only from validated
   artifacts. No push, tag movement, or release mutation has been performed
   for this candidate.
9. Update the marketing site and documentation with only real destinations and
   finish the P8.1 final validation report. The report must preserve the
   distinction between green CI for canonical `f0cb4b6...` and evidence for
   this unrelated local line.

## Stop condition

Stop after P8.1 final validation and the public-beta release status report.
At the current checkpoint, local product polish is validated but the overall
public-beta gate is not passed: canonical history reconciliation, a remote run
for this exact line, a P8.1 GitHub release, and `finathink.cloud` deployment
evidence are absent. Apple signing, notarization, and a signed DMG remain
explicitly deferred.
