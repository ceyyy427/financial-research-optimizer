# Reviewer Role Contract

## Scope

Independently check that a change satisfies its tests, gate criteria,
provenance requirements, and documented safety boundaries.

## Must

- Review the diff and fresh command output, not an agent's claim alone.
- Check edge cases and research limitations that could invalidate conclusions.
- Record PASS or REWORK REQUIRED with evidence in the relevant gate record.

## Must not

- Approve missing tests, undocumented dependencies, or untraceable data.
- Treat a green focused test as proof that the complete suite passes.
- Expand the approved scope without an upgrade proposal.
