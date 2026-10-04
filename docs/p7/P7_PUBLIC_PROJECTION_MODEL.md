# P7 Public Projection Model

Projection is an explicit, versioned release from a private source. The owner
chooses the source fingerprint, allow-listed fields, visibility, and version,
then gives consent. The repository sanitizes the payload and stores no fields
outside the allow-list.

Visibility is `PRIVATE`, `SHARED_ROOM`, `SHARED_GROUP`, or `PUBLIC`. Only
`SHARED_ROOM`/`PUBLIC` projections can be attached to a room post. Anonymous
read is limited to active public projections. A source fingerprint mismatch
blocks publication; a later mismatch marks an active projection `STALE`.

Revocation is immediate for reads and attachments while preserving the private
source and a minimal audit event. Re-publication requires a new version and a
new consent decision. The model supports future group visibility without
granting arbitrary cross-user graph access.
