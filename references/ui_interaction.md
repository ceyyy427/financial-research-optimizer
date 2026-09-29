# UI interaction contract

The HTML artifact is an independent, offline presentation layer. Python computes
all financial values; the renderer embeds only saved values, lineage, formulas,
source capability and manifest records. `scripts/ui/interaction.js` may change
visibility, sorting, filters, theme and disclosure state, but it must not fetch a
URL, fit a model, recompute RMSE/risk/weights, or relax a constraint.

## Local interactions

- Tabs: Overview, Why this forecast, Forecast, Risk, Portfolio, Provenance and Learning mode.
- Filters: model, source and declared time-range controls filter tagged saved elements.
- Charts: hover/focus reveals the value already stored on the SVG mark.
- Tables: sortable headers reorder existing rows only.
- Explanations: native `details` controls reveal formula source, evidence, calculation references and caveats.
- Theme: light/dark is a presentation preference; `prefers-color-scheme` remains the default.

## Explainable research and learning interactions

Every explanation card, formula card, learning card, source row, model row and chart mark carries `data-run-id` plus the relevant `data-claim-id`, `data-formula-id`, `data-calculation-id`, `data-source` and `data-index`. Clicking a claim displays the saved evidence and calculation references. Clicking a formula variable displays its saved definition, unit, current value and source; missing values remain `not_available`. Learning mode expands concept, derivation, example, failure boundary and self-test sections from `learning_cards.json`.

These interactions change selection and visibility only. They do not call `fetch`, `XMLHttpRequest`, WebSocket, Python or an external chart library. Scenario recalculation must use MCP `preview_scenario`, which writes a new scenario namespace and new explanation/learning/formula artifacts.

The UI distinguishes `observed`, `predictive`, `decision` and `causal_hypothesis`. Predictive contribution text must not be rendered as a causal claim.

## Runtime interactions

Scenario changes, model comparison refreshes, source refreshes and plan progress
are MCP/Python Runtime operations. They create a new `scenario_id` and immutable
artifacts; they never overwrite the base run. `preview_scenario` accepts only
declared bounded changes and rejects constraint relaxation or arbitrary code.

## Formula assets

`fro-formula-build --input knowledge_explanations.json --output formulas` writes
TeX sources and a `formula_manifest.json`. It reports `FORMULA_COMPILE_FAILED` or
`FORMULA_RENDER_FAILED` when a compiler/converter is unavailable or fails; it
never displays an uncompiled TeX string as if it were a rendered formula.
