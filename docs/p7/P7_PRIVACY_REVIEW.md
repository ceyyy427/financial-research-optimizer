# P7 Privacy Review

The first slice defaults all personal graph and mastery material to PRIVATE,
requires a named principal for export, and separates sanitized projections
from their sources. Revocation does not delete private history, which preserves
the owner's continuity while blocking public access.

Review checks: no session rows in export; no other principal ids in bounded
context; projection fields are allow-listed; public reads reject revoked or
room-only projections; deletion revokes projections before foreign-key
cascade. Open production follow-ups are consent UX copy, retention schedule,
data-subject support process, and encrypted backups.
