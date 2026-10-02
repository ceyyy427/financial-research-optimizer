# P6.5 Understanding Contract

## Contract purpose

Every complete event journey must let a person move from a source-bound fact to
a bounded test and a reusable learning state. The contract is progressive
disclosure: it is a set of inspectable outputs, not one confident AI summary.

The mission names **11 narrative/action slots plus the Learn artifact** (often
described as 11 outputs when learning is treated as the terminal state). The
implementation exposes all named slots below and makes the learning card/state
explicit, so no requested output is hidden by the count convention.

## Required outputs

| Slot | Product field/API | Required semantics | Evidence boundary |
| --- | --- | --- | --- |
| What happened | `what_happened` | Identify the admitted event, source, and reference period | direct event/source evidence |
| What changed | `what_changed` | State the measured change or newly available observation without hype | canonical observation + timing |
| Why it may matter | `why_it_may_matter` | Show a typed mechanism and its limitation | concept relations/theory evidence |
| What we know | `what_we_know` | Facts supported by direct evidence | only resolved claims |
| What the evidence suggests | `evidence_suggests` | Describe normalized quantitative/derived evidence | P6 result/evidence status |
| What is plausible | `plausible` | Bounded interpretation or mechanism hypothesis | explicitly marked interpretation/theory |
| What we do not know | `unknown` | Preserve unresolved causality, vintage, or future-return questions | `UNKNOWN`/`LIMITATION` claims |
| What would change the view | `what_would_change_view` | Name falsifying/revising evidence or a different pre-specified test | future evidence/test boundary |
| What to watch next | `what_to_watch_next` | Point to the next official release, revision, or test window | source/timing references |
| Show Evidence | `show_evidence` | Expand claim type, source, reference, timing, artifact/run, and limitations | `EvidenceBundle` or repository query |
| Test the idea | `test_idea` | Bind an event-scoped hypothesis to a typed P6 request | `ResearchQuestion`/`TypedToolRequest` |
| Learn | `learning_card`, `learning_state` | Turn the same evidence into a concept/formula/misconception/follow-up and record encounter state | existing P6 `LearningStore` |

## Conclusion ladder

The five required levels are represented by `ConclusionLadder` in this order:

1. `WHAT_WE_KNOW` — direct source/event facts;
2. `EVIDENCE_SUGGESTS` — what the normalized test or derived evidence says;
3. `PLAUSIBLE` — a mechanism or interpretation that remains bounded;
4. `UNKNOWN` — what the current source/test cannot establish;
5. `WHAT_WOULD_CHANGE_VIEW` — future evidence or a changed design that could
   revise the conclusion.

Every entry carries evidence IDs, and the ladder requires at least one explicit
limitation. Levels may not be collapsed into a single confidence score.

## Typed distinctions

The UI/API must keep `FACT`, `INTERPRETATION`, `HYPOTHESIS`, `QUANT_FINDING`,
`UNKNOWN`, and `LIMITATION` visually and semantically distinct. A theory edge
such as `Inflation → rate expectations → yields → discount rate → valuation`
is not proof that the CPI release caused a particular asset return. A historical
quant result describes its declared sample; it does not promise the next outcome.

## Progressive levels

`ProductJourney.progressive_levels` currently exposes:

```text
EVENT → MECHANISM → EVIDENCE → QUANT → DEEP_KNOWLEDGE
```

The event and mechanism can be read quickly; evidence opens source/capture
details; quant opens the typed run and limitations; deep knowledge opens
concept definitions, formulas, conclusion ladder, and learning follow-up.

## Completion criteria

A journey is incomplete if any required slot is empty, if Show Evidence cannot
resolve a claim, if a quant statement lacks a P6 result fingerprint, if a
limitation is missing, or if learning content introduces an unsupported fact.
The current deterministic product test asserts the slots, quant success,
conclusion ladder, prediction/reveal/explain object, and learning state.
