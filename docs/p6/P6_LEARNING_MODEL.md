# P6 Learning Model

## Learning cards

Each card is grounded in a definition or result and contains:

`Concept`, `Definition`, `Formula` (when applicable), `Result Context`,
`Interpretation`, `Common Misconception`, `Limitation`, and `Follow-up
Question`. Cards are generated from approved concepts such as lag, turnover,
beta, benchmark excess return, OOS evaluation, and survivorship bias. A card
cannot introduce a claim absent from the evidence bundle.

## Minimal state

The append-only learning state consists of `ConceptProgress`, `Misconception`,
`ReviewItem`, and `LearningThread` records. Every record includes `user_id`,
`concept_id`, encounters, correct/incorrect counts, confidence, last and next
review timestamps, and an evidence or card reference. Updates are deterministic
and preserve the prior state. There are no psychological labels; a
misconception is a structured observed response linked to the concept and
evidence.

## Predict/reveal/explain

Before evidence is revealed, the user may submit a prediction about the
direction or meaning of a result. `PREDICT` stores it without scoring against
the hidden result. `REVEAL` shows the normalized result and comparison. `EXPLAIN`
renders the grounded explanation and limitation. The three events and their
timestamps are part of the audit. A quiz question is generated only from the
card’s definition, formula, or grounded result and records its source.
