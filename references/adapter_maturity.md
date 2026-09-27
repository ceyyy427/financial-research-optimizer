# Adapter maturity and parser gate

Source profiles are capability declarations, not proof that a connector can
execute. Every profile must declare:

| Field | Values | Meaning |
|---|---|---|
| `implementation_status` | `planned`, `partial`, `production` | Whether the acquisition path exists and has an operational contract. |
| `parser_status` | `unavailable`, `partial`, `available`, `tested` | Whether the raw response can be converted into the declared canonical record. |
| `execution_ready` | derived | True only when implementation is `partial`/`production` and parser is `partial`/`available`/`tested`. |

`scripts/source_router.py --execute` rejects planned or parser-unavailable
profiles. A source selected for documentation may remain `planned`, but it
must never be used by `scripts/execute_online_refresh.py`. A parser marked
`available` or `tested` must be registered in `scripts/parsers/__init__.py`;
the registry validator checks this relation before a run.

`production` means that the adapter has an executable request path, preserved
raw response/snapshot metadata, a parser, point-in-time/revision semantics
appropriate to its profile, and tests. It does not mean the source is always
fresh, authenticated, or licensed for every user. Those conditions remain
runtime gates.
