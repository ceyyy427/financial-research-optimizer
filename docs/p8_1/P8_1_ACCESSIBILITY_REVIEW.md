# P8.1 Accessibility Review

**Review date:** 2026-10-03 (Asia/Shanghai)  
**Scope:** the server-rendered local application in `src/finahinking/local_app.py`
and the static launch page in `site/index.html`.  This is an implementation
review, not a conformance claim for a future hosted deployment.

## Review result

**PASS for the reviewed local shell, with manual-assurance items remaining.**
The shell has a stable landmark structure, a skip link, visible keyboard focus,
text labels for product states, responsive stacking, and a reduced-motion
fallback.  A screen-reader session, browser accessibility tree review, and an
axe/Lighthouse run were not performed in this pass, so WCAG conformance is not
claimed.

## Evidence collected

The following read-only probe rendered all ten product routes through
`LocalApplication.route("GET", ...)` and parsed the resulting HTML with
Python's standard-library `html.parser`:

```text
routes: /, /events, /explore, /knowledge, /knowledge/volatility,
        /quant, /strategy, /workspace, /community, /diagnostics
each route: lang=en, main=1, h1=1, nav>=1, aside=1,
            skip link present, aria-current="page" present
anonymous non-hidden controls: 0 on every route
```

The focused product tests also passed:

```text
.venv/bin/pytest -q \
  tests/p7_5/test_local_app.py \
  tests/p7_5/test_product_gate_real.py \
  tests/p7_5/test_e2e.py \
  tests/p6/test_gate_security_and_grounding.py \
  tests/p6/test_security_and_audit.py
23 passed in 4.67s
```

The source-level checks were:

```text
.venv/bin/python -m py_compile src/finahinking/local_app.py       PASS
.venv/bin/ruff check src tests scripts                              PASS
git diff --check                                                    PASS
```

## Implemented accessibility contracts

- Every application page is wrapped by one shared shell with `lang="en"`, a
  named primary navigation, one `main` landmark (`id="main"`), an optional
  inspector `aside`, a page title, and a single page-level `h1`.
- `Skip to content` is the first focusable link.  The shell marks the current
  destination with `aria-current="page"`; the concept route normalizes its
  active navigation to Knowledge.
- `:focus-visible` is defined for links, buttons, form controls, and `summary`
  with a 3px high-contrast outline and offset.  Controls and buttons have a
  minimum 44px height, and the responsive layout stacks the inspector below
  the workspace below 880px rather than requiring horizontal scrolling.
- Form controls have visible labels or an explicit wrapped label.  Required
  fields, character limits, and contextual help are present on question,
  hypothesis, idea, note, claim, consent, and learning forms.  Server errors
  use an actionable `role="alert"`; saved outcomes use a live status region.
- Status is expressed as words (for example `SAMPLE`, `OFFLINE`, `OOS`,
  `PAPER SIMULATION`, `UNKNOWN`, and `LIMITATION`) as well as color.  Claim
  types are written in the event page rather than conveyed by color alone.
- The primary launch image has descriptive alternative text.  The second
  launch frame is deliberately decorative (`alt=""`, `aria-hidden="true"`) and
  is only a visual transition frame.  The same rule is used by the static
  marketing page.
- The launch motion is finite CSS-only motion: the gradient ring and frame
  crossfade run for two iterations.  `@media (prefers-reduced-motion: reduce)`
  removes nonessential motion, disables transitions, and hides the decorative
  secondary frame.  No JavaScript animation or autoplay media is present.

## Color and typography spot check

The token palette was checked with the WCAG relative-luminance formula in a
read-only Python probe.  The lowest relevant token contrast was muted text
`#66777d` on the application background `#f5f7f7` at **4.34:1**, slightly below
the 4.5:1 normal-text target; it is reserved for secondary metadata and is
above the target when rendered on white (`4.67:1`).  Primary text is `14.96:1`
on the background, the focus teal is `6.20:1`, and white text on the primary
teal button is `6.67:1`.  If muted metadata becomes task-critical or is used at
small body-text sizes, darken that token before a hosted beta.
Metrics use tabular numerals and long code/equations wrap with
`overflow-wrap:anywhere`.

## Remaining manual checks before a hosted beta

1. Run axe (or an equivalent ruleset) against every route at narrow and wide
   breakpoints, including an error result and a populated Workspace.
2. Complete a keyboard-only pass: skip link, nav order, form error recovery,
   `details` disclosure, and inspector links.  Confirm focus remains visible
   after responsive stacking.
3. Test VoiceOver/NVDA announcements for the live result region, status words,
   the decorative image transition, and the claim ladder.
4. Recheck contrast after any brand-token change and verify the static page
   under the actual hosting headers.  This document intentionally does not
   certify an external browser or a hosted CDN configuration.
