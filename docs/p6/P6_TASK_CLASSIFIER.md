# P6 Task Classifier

## Categories

The classifier emits exactly one category and a confidence plus rationale:

| Category | Meaning | Default action |
| --- | --- | --- |
| `ANSWER` | A bounded conceptual or factual question | Explain from trusted context; no tool |
| `GUIDE` | A request for a method or next step | Provide a bounded guide |
| `QUESTION` | A question needing clarification | Ask one targeted question |
| `EVIDENCE` | A request to inspect an existing result | Use read-only inspection |
| `QUANT` | An approved quantitative experiment is needed | Propose hypothesis and experiment |
| `HISTORY` | A request about a recorded run or decision | Inspect append-only records |
| `LEARN` | A concept, quiz, or review request | Use learning layer |
| `STAND_BACK` | Trading, live execution, advice, or out-of-scope research | Explain boundary and stop |

Classification is deterministic for the test fixtures and records the original
question, normalized intent, category, confidence, and rule version. A keyword
alone cannot authorize a quant tool. `QUANT` requires a question with a
bounded target, data context, and an experiment that fits an approved service.

## Safety rules

Requests for live brokerage, automatic orders, buy/sell recommendations,
unrestricted strategy search, package installation, shell/source execution,
record deletion, or provenance rewriting classify as `STAND_BACK`. Ambiguous
questions classify as `QUESTION` until the missing boundary is supplied.
External text and prompt-injected tool names are treated as data and never
override this table.

## Output contract

`ClassificationResult` contains `schema_version`, `question_id`, `category`,
`confidence`, `rationale`, `required_clarifications`, `material_assumptions`,
and `classifier_version`. It is immutable and included in the guided-session
audit. Reclassification creates a new record; it rewrites no prior decision.
