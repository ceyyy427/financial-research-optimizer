# P8.2B Math Renderer Decision

## Audit

P8.2 used escaped equation strings inside `<pre><code>` blocks. The frontend
had no KaTeX/MathJax dependency and no CDN script. That is an acceptable
research fallback but does not satisfy the P8.2B education gate.

## Decision

Admit bundled KaTeX `0.19.0` as the single primary renderer. It is MIT
licensed, fast for repeated display equations, supports server/string
rendering, and can emit MathML for an accessible semantic fallback. The
browser bundle will be same-origin and committed under `site/assets`; normal
operation never fetches a CDN.

MathJax remains a reference candidate. Its broader accessibility and
expression exploration are valuable, but its runtime and bundle cost are not
justified for the current local-first surface. A future MathJax experiment
must be separately gated and cannot silently become a second renderer.

## Contract

`MathExpression` stores a canonical Finathink AST plus derived TeX. Server
rendering escapes user-facing text and emits KaTeX HTML/MathML only from
validated catalog expressions. Invalid expressions receive a readable
plain-text fallback and a validation error; they are never silently treated as
authoritative mathematics.

## Verification boundary

Deterministic tests verify renderer selection, offline asset presence, TeX
copy/export, and MathML markup. Real browser paint and screen-reader timing
remain a separate NOT VERIFIED gate when no approved browser is available.
