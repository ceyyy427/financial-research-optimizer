# Adapter maturity, evidence and parser gate

Source profiles are capability declarations, not proof that a connector can
execute. Maturity is evaluated per `source_id + dataset_id + access_method`
from `config/adapter_evidence.json` and the explicit factory, not by trusting a
single YAML label. Every profile should declare:

| Field | Values | Meaning |
|---|---|---|
| `implementation_status` | `planned`, `partial`, `production` | Whether the acquisition path exists and has an operational contract. |
| `parser_status` | `unavailable`, `partial`, `available`, `tested` | Whether the raw response can be converted into the declared canonical record. |
| `automatic_execution_ready` | derived | L3: factory, request contract, fixture, integration and quality evidence pass. |
| `live_certified` | derived | L4: L3 plus live smoke, healthy/fresh status, PIT/revision and snapshot evidence. |
| `degraded_execution_ready` | derived | True only when a real executable fallback exists. |
| `manual_review_only` | derived | Partial contract routed through `ContractOnlyAdapter`; not automatically fetchable. |
| `contract_only` / `blocked` | derived | Declared-only or planned capability; dependent analysis must stop. |

`scripts/source_router.py --execute` requires `automatic_execution_ready`; it
does not treat a partial parser as a fallback. A source selected for
documentation may remain `planned`, but it must never be used by
`scripts/execute_online_refresh.py`. A parser marked `available` or `tested`
must be registered in `scripts/parsers/__init__.py`; the registry validator
checks this relation before a run. `scripts/run_adapter_smoke.py` writes
replay/live evidence but does not silently promote a source to L4.

The current seven formal adapters are L3 executable. They are not L4 live
certified until the evidence manifest contains a passing live smoke, health,
freshness, snapshot hash, PIT/revision result and recent success. Secondary
aggregators such as Tonghuashun are executable for discovery/cross-check only;
`authority_primary_allowed` remains false. The nine partial sources are
`manual_review_only` until a real fallback fetch is implemented, and the five
planned sources are blocked.

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
