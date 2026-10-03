# P8.1 Capability Matrix

Recorded: 2026-10-03 (Asia/Shanghai). The matrix records actual capabilities
available before implementation and the evidence used for the candidate. No
new package or connector was installed because the required local capabilities
already exist. The final validation work itself uses shell/Git and local
loopback probes; it does not require Computer Use.

| Capability | Task | Existing tool / skill | Available | Trusted | Needs installation | Installed | Permissions / boundary | Actual usage |
|---|---|---|---|---|---|---|---|---|
| Planning and verification | execution sequencing and completion evidence | `superpowers:writing-plans`, `superpowers:verification-before-completion` | YES | YES | NO | YES | local repository only | plan and final gate review |
| Repository inspection | state, history, diffs, ancestry | Git CLI | YES | YES | NO | YES | local checkout; no destructive reset | baseline and remote classification |
| GitHub identity/CI/release | auth, workflows, release | authenticated `gh` CLI | YES | YES | NO | YES | account-scoped GitHub operations; secrets remain in keyring | auth and remote evidence audit |
| UI design reasoning | design system and IA | `frontend-design`, `design-system`, `ui-ux-pro-max` | YES | YES | NO | YES | local docs and source | design-system search and audit |
| Browser visual QA | rendered journey and screenshots | Codex CUA/browser capability | YES | YES | NO | YES | loopback local app only | representative visual review was available; no external browser or hosted surface is treated as release evidence |
| Application runtime | local HTTP journeys | Python stdlib server + project scripts | YES | YES | NO | YES | loopback-only, offline sample mode | smoke/E2E validation |
| Accessibility review | keyboard, semantics, focus, contrast, motion | UI/UX Pro Max quick reference + browser inspection | YES | YES | NO | YES | no external data | implementation and review |
| Test runner | regression and focused tests | `.venv/bin/pytest` | YES | YES | NO | YES | local files | full and focused suites |
| Static quality | lint and governance | `.venv/bin/ruff`, `scripts/validate_governance.py` | YES | YES | NO | YES | local files | release gates |
| Dependency/security | dependency and secret checks | `.venv/bin/pip-audit`, `scripts/secret_scan.py` | YES | YES | NO | YES | package metadata and repository | release gates |
| Packaging | wheel and clean-install | `scripts/clean_install.py`, `scripts/prepare_release.py` | YES | YES | NO | YES | temporary venv outside source tree | release gates |
| Notebook validation | reproducible research workflow | Jupyter/nbconvert in `.venv` | YES | YES | NO | YES | deterministic fixture | release gate |
| GitHub MCP/structured connector | remote inspection | no dedicated connector exposed in this task | NO | N/A | NO | NO | use authenticated `gh`/Git instead | documented capability gap; no install needed |
| Frontend framework/package | component system | existing inline server-rendered HTML/CSS | YES | YES | NO | YES | CSP forbids scripts; avoid dependency expansion | retained; no package added |
| Launch imagery | static brand orientation frames | user-provided JPEG assets, packaged under `site/assets/` and `_package_data/assets/` | YES | YES | NO | YES | explicit two-file asset allow-list; no arbitrary file reads | served locally and used as finite crossfade/gradient launch frames |
| Canonical remote | repository, CI, release inspection | exact GitHub URL + authenticated `gh`/Git | YES | YES | NO | YES | read-only audit at this checkpoint; no force push | identity, `main`, CI runs, and `v1.3.0` inspected; local/remote histories are unrelated |

## Current gate interpretation

- Local runtime, dual-environment tests, Ruff, notebook, pip checks,
  `pip-audit`, secret scan, migration verification, wheel clean-install, and
  sample launch are green for the candidate recorded in the final report.
- `scripts/validate_governance.py` now recognizes `P8.1` and the complete
  report set; the current run is PASS. A clean committed worktree is still
  required before calling the local release gate PASS.
- The canonical repository is public and reachable, but its `main`/release
  line has no merge base with this checkout. Its green CI is therefore not
  evidence for the local candidate; publication remains conditional on a
  deliberate history strategy.

The absence of a dedicated GitHub MCP is not a blocker because authenticated
`gh` and normal Git operations provide the required repository, workflow, and
release evidence. Installing another connector would add capability without a
demonstrated gap.
