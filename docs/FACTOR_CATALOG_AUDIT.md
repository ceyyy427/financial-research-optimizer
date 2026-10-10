# Factor catalog audit boundary

The autonomous research pipeline emits controlled, paper-only factor
proposals. Every proposal is represented by a `FactorCatalogEntry` containing
its version, source identifiers, reviewed license status, point-in-time
semantics, required fields, and research fingerprint.

The catalog is an audit record, not the production factor registry. Missing or
unapproved source licensing, unknown PIT semantics, empty source metadata, and
future-looking fields fail closed. A human admission record is required before
an entry can be considered admitted; the pipeline never mutates
`FactorRegistry`.
