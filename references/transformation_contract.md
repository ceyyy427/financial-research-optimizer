# Browser/API transformation contract

Raw HTML, JSON, CSV, Excel, and PDF are immutable evidence, not model tables. Transformations must emit a canonical row with `instrument_id`, `observation_time`, `availability_time`, `effective_time`, `field`, `value`, `unit`, `currency`, `adjustment`, `source_id`, `snapshot_hash`, and `transformation_id`.

The transformation stage must state field mapping, unit normalization, timezone normalization, duplicate policy, adjustment convention, and schema version. A rendered page value that conflicts with a captured API response is a source reconciliation finding. A revised or unavailable value cannot be silently replaced by the latest value.
