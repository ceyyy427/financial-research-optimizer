# Source health and routing

Static authority and adapter maturity are insufficient for online routing. Each provider may report `source_health`, `last_success_at`, `last_failure_at`, `latency_ms`, `schema_version`, `provider_status`, and `license_expiry`.

Routing order remains authority → capability → implementation maturity → health → freshness → cost. A failed provider is rejected. A stale or degraded provider may be used only as a declared fallback, with its status copied into provenance, HTML and the decision table. Health telemetry never relaxes authorization, point-in-time, source conflict, or research constraints.
