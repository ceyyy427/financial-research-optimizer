# P8.1 Information Architecture

Finathink is organized around user questions and evidence, not internal run
identifiers.

## Primary worlds

1. Home — what can I understand or continue today?
2. Events — what happened, what changed, and why might it matter?
3. Explore — a cross-journey starting point for saved events, concepts, and
   research.
4. Knowledge — progressive depth from intuition through current context.
5. Quant — question, hypothesis, data, method, result, uncertainty, and
   learning.
6. Strategy Lab — idea through StrategySpec, feature lineage, backtest, OOS,
   paper, comparison, and export.
7. Workspace — human-named continuity across research, strategies, paper runs,
   learning, and exports.

Community remains a guarded discussion/projection destination, private by
default. Diagnostics remains a secondary support destination. The legacy
`/personal` path resolves to Workspace for compatibility; it is not a second
information architecture. Artifact IDs and internal run names remain
detail/provenance labels rather than primary navigation.

## Journey transitions

- Events can continue into a knowledge concept, a private learning thread, or
  a bounded Quant question. `Show Evidence` stays on the event surface and
  does not replace the source/provenance context.
- Knowledge concept pages expose the same eight levels and retain
  prerequisites, assumptions, misconceptions, mastery, and source links.
  Search with no match returns an actionable empty state rather than a dead
  route.
- Quant and Strategy POST results render as saved research in Workspace. The
  result page keeps the metric, meaning, non-meaning, uncertainty, code/math
  mapping, provenance, OOS/paper validity, and a return path visible.
- Workspace is the continuity handoff for saved events, learning evidence,
  quant artifacts, strategy artifacts, and exports. Empty state copy points to
  Events or Quant so a new user can recover without knowing an internal ID.
- Community writes remain private until the explicit projection consent and
  field allow-list are supplied. No leaderboard, broker, or live-trading path
  is part of the primary architecture.

## Shared reading order

Every substantive page answers: What am I looking at? Where did it come from?
What does it mean? What does it not prove? What can I learn next?

## Responsive behavior

Wide screens use navigation + workspace + optional inspector. Narrow screens
stack navigation above the workspace and move inspector content below the main
result; no essential evidence is hidden behind hover or horizontal scrolling.

## Route contract

The shared shell currently covers `/`, `/events`, `/explore`, `/knowledge`,
`/knowledge/<concept>`, `/quant`, `/strategy`, `/workspace`, `/community`, and
`/diagnostics`. Browser-facing errors are rendered as recoverable HTML pages;
JSON/API routes remain explicit machine-readable contracts. The inspector is
optional but present on substantive pages so source, method, privacy,
uncertainty, and execution boundaries remain discoverable.
