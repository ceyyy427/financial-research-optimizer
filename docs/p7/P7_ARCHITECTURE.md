# P7 Personal Intelligence and Evidence-Driven Community Architecture

## Mission and authority

The 2026-10-03 P6.6 Final Validation + P7 mission is authoritative. It supersedes
the earlier P3 delivery stop without deleting its historical evidence. P6.6
must pass a repaired, post-commit gate before P7 product implementation starts.
The user requested autonomous intermediate gate completion; this design and its
plan are reviewed by independent agents instead of requiring repeated human
intervention. P8 is not authorized.

## Design choice

Extend the existing Python domain services and additive relational migrations,
using the existing SQLite development adapter and PostgreSQL target schema.
This gives deterministic identity, ownership, evidence references and revocation.
A separate graph/vector database would duplicate identity and ownership without
a measured need. A hosted community service would introduce unrelated data
processors and external publication; neither is admitted.

Two separate domains share explicit authenticated principals and immutable
artifact references: P7A owns private continuity; P7B consumes only user-approved,
versioned projections. Community content never becomes private truth implicitly.

## Frozen authorities

- P4 ResearchRun/RunStore remain research record authorities.
- P5/P5.5 QuantRun/backtest/OOS ledgers remain quantitative authorities.
- P6 LearningCard, Misconception and LearningThread are reused as learning data,
  extended by persistent evidence records rather than an opaque memory store.
- P6.5 Event/Claim/Evidence/Concept/KnowledgeBridge and source admission remain
  factual authorities; content labels are preserved.
- P6.6 StrategyVersion/FeatureVersion/PaperRun/export remain strategy authorities.

P7 stores immutable reference envelopes and private relationships, not a second
execution engine. Artifacts keep their source identity, fingerprint, limitations,
versions and code commit; no personalized service recalculates or rewrites them.

## Personal domain

Typed private nodes and relations form an owner-scoped graph. Mastery is derived
from explicit quiz, prediction, application, correction and transfer evidence,
not an AI score. Every state returns its supporting evidence and an explanation.
Misconception records preserve detected/corrected timestamps and evidence.
Learning threads connect ordered concepts, encounters, weaknesses and artifact
references. Saved objects, research/strategy history and timeline are relational
views over the same artifact catalog, avoiding duplicate canonical histories.

Guidance retrieves a purpose-scoped, bounded context slice for one authenticated
owner. It can change explanation depth and optional review prompts only. It
cannot alter quantitative/factual payloads. No wealth, political, health or
unrelated behavioral profile is stored.

## Community and projection domain

Start with one Research Room, membership permissions, typed claim-first research
posts and natural educational questions, comments and evidence attachments.
Private source objects are never directly attached. The owner explicitly selects
fields and visibility; a projection builder copies an allowlisted public shape,
preserves mandatory provenance/limitations and removes private IDs, notes and
hidden metadata. A fresh projection version is created for revised source data.
Revocation denies future projection and attachment reads without deleting or
mutating the private source. An explicit save action creates a private question
from community discussion, retaining attribution and uncertainty.

Community summaries are attributed data structures (agreement, disagreement,
support/counter-evidence, unknowns and testable questions), not consensus claims.
Moderation covers spam, harassment, malicious links and financial overclaims
without treating disagreement as misconduct. Quality indicators measure evidence,
reproducibility and limitations rather than popularity or user intelligence.

## Trust boundaries

P7 identity is established by a trusted local application authority; service calls
must resolve a registered session/principal, not accept arbitrary actor IDs as
authorization. Owner and room permissions are enforced on every read/write,
attachment, export, deletion and context retrieval. SQL is fixed and parameterized.
Community text is untrusted data, never SQL, shell, tools or model instructions.
Rendered content is escaped; link references are validated. Direct database
administrators remain outside application isolation guarantees.

## Persistence, deletion and recovery

Migration 003 extends the same schema with identity/ownership, typed relations,
evidence, threads, history links, room membership, projections and discussion.
Foreign keys and uniqueness prevent orphan references and duplicate grain.
User export is structured, owner-authorized JSON without credentials/sessions.
Verified deletion removes private state and derived mastery, revokes projections
and removes access through community attachments; minimal non-content audit
records may remain with documented scope. Migration rollback is additive-table
removal only in a disposable development database; never reset user data.

## Product and operational scope

Provide inspectable Personal Home, graph/thread/timeline views, relevant guidance,
room discussion and an explicit preview/share/revoke flow using repository-native
interfaces. Progressive disclosure keeps evidence and privacy choices visible
without an overwhelming dashboard. Authentication, multi-user persistence and
privacy must be exercised by real integration tests, not presentation-only mocks.
This is a locally validated research product slice, not a production social network.
Production identity federation, distributed sessions, moderation staffing,
availability, backups and scale are separate readiness decisions, not hidden claims.

## Acceptance and ownership

Finathink maintainers own the services, migration and policies. Security,
privacy, data quality and reproducibility reviews must independently reject
unsupported claims. Both strategy→personal→community→new-question and real
CPI-event→personal-learning→optional-projection journeys must work. All 44 P7
gate items and 89 mission sections are traced to inspected current evidence.
No P7 PASS until every required behavior and post-commit command is verified.
