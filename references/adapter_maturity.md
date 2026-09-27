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

## Tonghuashun (`10jqka`)

The Tonghuashun adapter executes public daily-line JSONP snapshots through:

```text
scripts/browser/navigation.py
  -> scripts/adapters/tonghuashun.py
  -> scripts/parsers/tonghuashun_jsonp.py
  -> scripts/normalize_observations.py
  -> scripts/source_snapshot.py
```

It preserves the raw response and records `latest_only` and
`point_in_time_status=not_available`. It is suitable for discovery,
cross-checking, and degraded research, but is not a point-in-time primary
source when an official exchange or licensed historical series is available.

TLS verification is enabled by default. `FRO_TLS_INSECURE=1` is an explicit
operator override and is recorded in snapshot metadata. Install the browser
runtime before live execution:

```bash
python3 -m pip install -e '.[browser]'
python3 -m patchright install chromium
```
