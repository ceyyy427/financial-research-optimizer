# Privacy and local data

Finahinking is local-first. By default, research runs, personal learning
state, saved strategies, community drafts, and the local SQLite database stay
on the user's machine. The app does not require an account or telemetry for
sample mode.

## Network behaviour

- Sample mode reads reviewed fixtures only and can run offline.
- An explicit provider action may contact an allowlisted official source such
  as BLS. The request, retrieval time, payload hash, parser version, and
  source status are retained as provenance.
- An optional AI/provider call is never implicit. The diagnostics surface must
  state which provider is contacted, why, and whether the request includes
  user content. API keys are process configuration and are never logged.
- No broker/order endpoint, cloud sync, hosted account, or real-money path is
  present.

## Files and backup

The local database and exported artifacts are user data. Back up the database,
artifacts, research exports, and any configured fixture directory together;
keep backups outside the source checkout and protect them with the user's OS
controls. Before sharing diagnostics, remove credentials, tokens, private
research, and unnecessary absolute paths.

## Telemetry

There is no required telemetry in the public beta. If telemetry is introduced,
it must be opt-in, documented before collection, and must not upload private
research or learning data by default.

## Retention and deletion

Users control local files and can delete their local database/exports. A
provider's own retention policy applies to an explicit outbound request; read
the provider terms before enabling it. Finahinking does not claim to delete
data from an external source it does not control.
