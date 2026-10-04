# P8.2B Education and Accessibility Gate

## Implemented locally

- MathML is server-rendered beside a readable LaTeX string; KaTeX enhances
  the equation when the local bundle loads.
- Equation cards, symbols, derivations, assumptions, limitations, references,
  and code segments have semantic headings and text fallbacks.
- Code selection uses keyboard-operable buttons with a line range and an
  input/output inspector. The research table remains available without
  JavaScript and emits the same canonical point IDs when the bundle is live.
- Context status, selected observations, errors, and widget outcomes use text
  rather than color alone. Reduced-motion CSS is retained for the research
  workspace and launch assets.
- The `/research` observation rail links to
  `/knowledge/volatility?context_type=research_point&context_id=...`, so a
  learner can move from a selected value to a point-in-time explanation.

## Evidence and honest limits

Python contract, route, export, widget, and frontend schema tests pass. The
server-rendered fallback is covered by local route tests. Browser paint,
screen-reader timing, mobile-device layout, and real assistive-technology
verification are **NOT VERIFIED** in this checkpoint because the mission and
user instruction prohibit Computer Use and no approved headless browser gate
was available. This report therefore makes no browser-level accessibility
claim.

The next approved gate should run keyboard traversal, MathML/KaTeX inspection,
screen-reader announcements, reduced-motion checks, and mobile viewport tests
in a permitted browser environment without weakening the no-arbitrary-code or
same-origin constraints.

