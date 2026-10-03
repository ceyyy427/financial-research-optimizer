# P7.5 accessibility review

The local shell passes a basic semantic/accessibility review:

- every page has `lang="en"`, a document title, one `main`, and navigable
  headings;
- a visible keyboard-accessible “Skip to content” link precedes navigation;
- navigation uses an `aria-label` and ordinary anchors, so it works without
  JavaScript;
- the layout is responsive through a viewport declaration and readable line
  width; state labels also contain text, not colour alone;
- code/equation content is rendered as text and remains copyable;
- no autoplay, animation, canvas, or pointer-only interaction is required.

Follow-up for a richer UI: run an automated axe scan and a screen-reader pass
before adding a packaged desktop shell. The current stdlib surface deliberately
has no JavaScript dependency to keep this review reproducible offline.
