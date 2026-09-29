# L4 online certification

L4 is a capability-level status, not a source website label. The identity is
`source_id + dataset_id + access_method`. An explicit live smoke artifact must
show a successful formal fetch, non-empty observations, snapshot hash, healthy
provider status, fresh data, point-in-time/revision evidence, and a recorded
success time. Schema drift, stale data, missing authorization, replay-only
evidence, or an absent expiry blocks certification.

Use:

```bash
python3 scripts/run_adapter_smoke.py --mode live ... --output artifacts/smoke/live.json
python3 scripts/certify_adapter.py --smoke artifacts/smoke/live.json \
  --expires-at 2026-10-29T00:00:00Z
```

The second command is a dry decision. Add `--write` only after reviewing the
raw snapshot, normalized observations, and the printed blockers. No automatic
promotion is performed by routing, CI, replay, or the smoke command.
