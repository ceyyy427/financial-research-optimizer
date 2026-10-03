# P7 Permission Model

Authorization is capability-based and fail-closed. A session resolves to one
active principal; suspended, deleted, revoked, or expired sessions cannot
access P7 data.

## Operations

| Operation | Required authority |
| --- | --- |
| Read/update personal node | Node owner |
| Add graph edge/mastery evidence | Owner of every referenced node |
| Create room | Authenticated principal; becomes owner |
| Read room/post | Active member |
| Create post/comment | Authenticated active member matching author id |
| Attach projection | Post author; projection ACTIVE and SHARED_ROOM/PUBLIC |
| Publish projection | Source owner, current fingerprint, explicit consent |
| Revoke projection | Projection owner |
| Anonymous projection read | ACTIVE PUBLIC projection only |
| Export/delete personal data | Authenticated principal matching owner |

Room ownership is not a bypass for private graph access. Moderation is scoped
to room content and cannot read a member's private nodes. Cross-user reads,
foreign graph edges, guessed identifiers, and stale projections return a
permission error rather than partial data.

All rows are accessed with bound parameters. Identifiers are opaque values and
are never interpolated into SQL. Audit events record publication, revocation,
and deletion actions without copying private payloads.
