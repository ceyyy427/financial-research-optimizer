# P7 Mastery Model

Mastery is an explainable state, not a personality label or a claim of
competence. It is recomputed from typed evidence attached to a private concept.
The initial states are `NEW`, `EXPOSED`, `DEVELOPING`, `APPLIED`, `ROBUST`, and
`NEEDS_REVIEW`.

An incorrect outcome moves a concept to `NEEDS_REVIEW` until a correction is
recorded. One successful exposure is `EXPOSED`; repeated successful transfer
and application can move the state through `DEVELOPING` and `APPLIED`; a
repeated sequence of correct/application evidence may support `ROBUST`. The
state stores evidence ids and a human-readable explanation, so a user can
inspect why it changed and challenge it.

The model is intentionally conservative: neutral evidence does not increase
confidence, one correct answer does not prove mastery, and a public projection
does not change mastery. Evidence is append-only in the first slice; correction
is represented as a new typed outcome rather than rewriting history.
