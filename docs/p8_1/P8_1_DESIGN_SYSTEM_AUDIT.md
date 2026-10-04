# P8.1 Design System Audit — Baseline and Decision

The UI/UX Pro Max design-system search produced a restrained Swiss/editorial
direction for a research product. The generated recommendation is retained in
`design-system/finathink/MASTER.md` as research input; the application adapts
it to local-first operation by using system fonts and no remote font import.

## Semantic token set

The implementation will use semantic custom properties for background, surface,
elevated surface, border, primary/secondary/muted text, focus, information,
success, warning, error, evidence, fact, interpretation, hypothesis,
quant-finding, unknown, limitation, and learning. Product colors describe
evidence and research state; they do not imply buy/sell recommendations.

## Primitive decisions

- Typography: system UI for dependable offline rendering; tabular numerals for
  metrics; readable measure for long explanations; distinct labels for source,
  math, code, result, and limitation.
- Layout: 4/8px spacing rhythm, responsive grid, persistent left navigation on
  wide screens, collapsible/stacked navigation below 900px.
- Surfaces: quiet neutral background, white/elevated panels, one restrained
  navy-teal accent, visible borders, and no persistent decorative gradients or
  blobs. The only gradient is the finite, low-contrast launch halo requested
  for the two static brand frames; it is removed/short-circuited for reduced
  motion.
- Controls: native links, buttons, labels, fieldsets, visible focus ring,
  minimum 44px control height, and stable hover/pressed states.
- Status: one vocabulary — READY, RUNNING, COMPLETE, LIMITED, UNAVAILABLE,
  FAILED, SAMPLE, OFFLINE, OOS, PAPER — always paired with text, never color
  alone.
- Motion: only bounded state transitions and the finite launch-frame
  crossfade/halo; `prefers-reduced-motion` disables nonessential transitions
  and hides the decorative secondary frame.
