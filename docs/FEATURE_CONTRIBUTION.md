# Feature contribution contract

Every quantitative feature must declare a stable `FeatureDefinition` with:

- name, version, formula, units, and required inputs;
- availability/timing rule and look-ahead policy;
- missing-value, warm-up, and revision semantics;
- lineage to source observations and the `ResearchRun`;
- deterministic implementation and edge-case tests;
- an interpretation in finance and a learning explanation;
- realistic limitations, especially leakage, survivorship, and multiple
  testing.

Feature output must be reproducible from recorded inputs and must not be
presented as a signal or recommendation. Changes to a feature's formula or
timing require a new version and an explicit migration/compatibility note.
