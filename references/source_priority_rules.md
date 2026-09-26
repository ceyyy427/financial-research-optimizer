# Source Priority and Conflict Rules

Source selection is capability-aware. Authority does not override a missing point-in-time field, and freshness does not override an unresolved material conflict.

| Source class | Default role | Research-grade rule |
|---|---|---|
| exchange, regulator, central bank, statistics agency | primary | preferred when fields and timestamps are complete |
| licensed provider or authorized database | primary/cross-check | allowed only with authorization evidence |
| public API with revision/vintage support | primary/cross-check | use the declared vintage or release timestamp |
| secondary aggregator | discovery/cross-check | cannot be sole authority when an official source is available |
| library adapter | access layer | retain the underlying provider in provenance |

Stop dependent analysis when prices or volumes exceed declared tolerances, adjustment conventions differ without a declared conversion, calendars cannot be reconciled, effective timestamps are missing, or a licensed source is unauthorized/expired. A stale or failed primary source may use a cached snapshot only when its age and vintage are visible in the output.
