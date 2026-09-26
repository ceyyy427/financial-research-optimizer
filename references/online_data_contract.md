# Online data and snapshot contract

Use the provider registry in `scripts/online/provider_registry.py` in this order: official API, official download, official webpage, authorized database, trusted mirror, public scrape. API clients use `HttpCache`, `RetryPolicy`, and `SnapshotStore`. Every request records request URL/parameters, retrieval time, HTTP status, provider version, response hash, raw file, license, cache expiry, and revision policy.

FRED/ALFRED requests must preserve real-time/vintage parameters. SEC requests must use a descriptive contact User-Agent and preserve filing dates. ECB and BIS requests preserve SDMX flow/key and release window. API keys are read only from named environment variables and are redacted from cache keys and manifests.

An online result has one of `ready`, `stale`, `degraded`, `fallback`, or `blocked`. Stale cache may support descriptive historical analysis when explicitly allowed, but it cannot silently produce a real-time conclusion. Missing raw responses, failed hashes, empty API results, provider switches, or unresolved revisions are audit findings.
