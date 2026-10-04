# P8.1 Product Polish Report

Recorded: 2026-10-03 (Asia/Shanghai)

Status: local implementation complete; final gate re-run and canonical
publication remain separate release decisions.

## Outcome

P8.1 turns the existing server-rendered local application into one coherent
Finathink product without introducing a client-side framework or widening the
execution boundary. The product now presents a persistent navigation layer, a
primary workspace, and an optional evidence/context inspector. Internal IDs
remain available for provenance, but the first-level experience is organized
around user questions, learning, and reproducible research.

## Shared shell and interaction language

- A responsive shell now provides Home, Events, Explore, Knowledge, Quant,
  Strategy Lab, Workspace, Community, and Diagnostics destinations.
- The active destination is exposed with `aria-current`; a skip link, visible
  focus treatment, native form labels, and 44px controls support keyboard use.
- The right-side inspector names source, method, storage, privacy, uncertainty,
  and execution boundaries instead of hiding them behind an opaque artifact
  identifier.
- A semantic status vocabulary distinguishes evidence, facts,
  interpretations, hypotheses, quantitative findings, unknowns, limitations,
  learning, offline state, OOS state, and paper simulation. State is expressed
  in text as well as color.
- Empty, error, and saved-result surfaces point to a recovery or continuation
  action rather than ending in a dead state.

## Journey-level polish

| Journey | P8.1 result |
|---|---|
| Home | Explains what Finathink is for, exposes both research loops, shows private continuity, and provides direct starts for Events and Explore. |
| Events | Separates fact, interpretation, hypothesis, quantitative finding, unknown, and limitation; `Show Evidence` exposes the reason and provenance chain. |
| Explore | Starts from a human question and routes to event evidence, knowledge, quant research, or a paper-only strategy workflow. |
| Knowledge | Makes an eight-level path visible: intuition, definition, equation, derivation, proof boundary, code, finance/quant/strategy role, and current context. Assumptions, prerequisites, misconceptions, mastery, and sources stay attached. |
| Quant | Uses a staged question/hypothesis/data/method/result/uncertainty/learning flow and keeps sample, period, method, confidence interval, provenance, and limitations visible. |
| Strategy Lab | Carries one `StrategySpec` through feature lineage, code/math/finance meaning, backtest, OOS, paper simulation, comparison, validity, and learning. It offers no broker or live-trading action. |
| Workspace | Reopens research, learning evidence, paper runs, and exports by human-readable names while preserving local IDs as provenance details. |
| Community | Retains private-by-default projection, explicit consent, allow-list boundaries, and no leaderboard/pump-and-dump mechanics. |
| Diagnostics | Keeps redacted support and export paths secondary to the product journeys. |

## Launch imagery and motion

The two user-provided static images are now first-class local product assets:

- `finathink-splash-map.jpg` is the wide capability map.
- `finathink-research-splash.jpg` is the square research-workspace composition.

Both assets are packaged with the Python application and mirrored under the
static site. The home screen and `site/index.html` use them as launch frames,
not as evidence-bearing charts. A restrained conic-gradient halo rotates twice
over 18 seconds while the two frames crossfade for two 14-second cycles. The
motion terminates instead of running forever. The secondary frame is lazy
loaded and decorative to assistive technology; the primary frame has a useful
alt description. `prefers-reduced-motion` collapses the sequence to one static
frame and removes nonessential motion.

## Design and implementation boundaries

- The implementation keeps the existing Python/HTML/CSS stack and CSP rather
  than adding a JavaScript runtime or remote font dependency.
- System fonts keep offline rendering deterministic. Cards, borders, spacing,
  type scale, and status treatments share semantic tokens.
- The responsive layout changes from navigation/workspace/inspector to stacked
  regions below the defined breakpoints; essential evidence is not hover-only.
- Assets are served through an explicit filename allow-list and packaged as
  local JPEGs. They do not create arbitrary file access.
- Finance outputs remain educational and research-only. Strategy execution is
  explicitly `PAPER SIMULATION`; real-money actions are unavailable.

## Evidence recorded so far

- Focused UI and route assertions cover the shared shell, active navigation,
  inspector, launch assets, reduced-motion CSS, evidence language, knowledge
  search, Quant, Strategy Lab, Workspace, and asset responses.
- A real loopback HTTP smoke exercised Home, Events, Explore, Knowledge search,
  a concept page, Quant, Strategy Lab, Workspace, Community, Diagnostics, both
  image assets, and a CSRF-protected Quant POST; every exercised request
  returned the expected successful response.
- The most recent recorded full environment runs before the final result-view
  refinement were `276 passed, 1 skipped` in both `.venv` and `.venv-quant`.
  Those results are supporting evidence, not a substitute for the final gate
  re-run required by `P8_1_FINAL_VALIDATION_REPORT.md`.

## Remaining release boundary

This report validates local product polish only. It does not claim that this
P8.1 tree is on canonical GitHub, has passed GitHub Actions, is represented by
the existing `v1.3.0` release, or is deployed at `finathink.cloud`. Those states
are governed by the history, remote CI, release, and final-validation reports.
