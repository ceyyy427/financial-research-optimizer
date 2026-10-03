# P7 Privacy Model

P7 is private by default. A personal node, edge, mastery record, learning
thread, research history entry, strategy history entry, saved object, and
artifact link is owned by exactly one principal. The repository enforces that
ownership on every read and write; UI conventions are not a security boundary.

## Data classes

| Class | Default | Allowed disclosure |
| --- | --- | --- |
| Personal graph and mastery | PRIVATE | Owner, after authenticated session |
| Research/strategy history | PRIVATE | Owner; bounded authorized context |
| Projection | PRIVATE/DRAFT | Only after explicit consent and field allow-list |
| Room post/comment | Room-scoped | Active room members |
| Public projection | PUBLIC | Sanitized fields while ACTIVE |
| Audit event | Restricted | Operators under an audited support path |

Private source payloads never become public by joining a room. A projection is
a new object with a source fingerprint, version, visibility, selected fields,
and revocation state. Revocation blocks future reads while retaining the
private source for the owner.

## Retention and deletion

Export includes only the authenticated owner's graph, evidence, mastery,
history, and projection metadata. Personal deletion revokes projections,
deletes private graph rows through foreign keys, and retains a minimal audit
record so the deletion itself is accountable. No raw credentials, session
secrets, or hidden prompt content are stored in the P7 tables.

## Threat assumptions

The model assumes an untrusted client, malicious room member, SQL injection
attempt, stale source, and prompt-injected content. Parameterized SQL,
principal/session checks, allow-listed projection fields, current fingerprints,
and claim labels are mandatory controls. Confidentiality does not imply truth:
public visibility never upgrades an unverified claim.
