# P6 Explanation Contract

An explanation is a structured record, not a second calculation. It contains
the following ordered sections:

1. **WHAT WAS ASKED** — the user question and classification.
2. **WHAT WAS TESTED** — hypothesis, null, experiment, and frozen assumptions.
3. **DATA** — dataset/provider, period, universe, availability semantics, and
   fingerprints.
4. **RESULT** — normalized metrics and uncertainty copied from the evidence.
5. **WHAT IT SUPPORTS** — claims directly supported by the result.
6. **WHAT IT DOES NOT SUPPORT** — claims excluded by design or evidence.
7. **LIMITATIONS** — every P5.5 warning and limitation, including survivorship,
   delisting, corporate actions, liquidity, capacity, and market impact where
   applicable.
8. **CONCEPTS** — one or more learning cards grounded in the result.

Quantitative values carry a `claim_id`, source kind and source fingerprint.
The renderer refuses a numeric claim without a matching normalized evidence
field. It cannot invent significance, causal language, future performance,
tradability, or advice. Undefined metrics remain `null` and are explained as
undefined. An interpretation is clearly labelled and cannot be presented as an
empirical result.

The explanation version, evidence IDs, warnings, limitations, and rendering
policy version are stored in the guided-session audit.
