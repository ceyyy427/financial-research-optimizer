# P8.1 UI Audit — Baseline

Status: baseline / remediation in progress.

The existing product is a useful server-rendered local application, but its
presentation is a single centered column with inline per-page styles. It has
the right domain journeys but does not yet expose them as one coherent product
shell.

## Baseline findings

- Navigation is a horizontal link string rather than a persistent left-side
  product hierarchy; there is no Explore/Workspace world.
- Home is a short list of links and does not surface continue-learning,
  current-research, or paper context.
- Events expose claims and evidence, but claim types and the “why this is being
  said” chain are not visually distinct.
- Knowledge has progressive content in the data model, but the page reads as a
  sequence of generic articles and does not make the eight-level path or
  prerequisites scannable.
- Quant and Strategy pages expose a form, but not a staged preview/result
  surface with uncertainty, validity, and paper-only boundaries.
- Personal continuity is present in the API but the page is not a human-named
  workspace.
- Empty, loading, and actionable error states are not shared primitives.
- Focus, reduced-motion, responsive layout, and semantic status vocabulary are
  not centralized.

## P8.1 target

Implement a shared shell: left navigation, primary workspace, and an optional
inspector/context rail. Preserve server-rendered HTML and the existing CSP.
Create reusable semantic tokens and components before page-specific content.

