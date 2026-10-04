# P6.5 Temporal and Revision Model

## Five clocks, five meanings

P6.5 does not collapse an economic observation into one ambiguous timestamp.
All populated times are ISO-8601 values with an explicit timezone.

| Field | Meaning | CPI example | Can it be inferred locally? |
| --- | --- | --- | --- |
| `occurred_at` | When the economic period/event occurred | first instant of `2024-12` for the December index period | Only as a declared period convention; it is not publication time |
| `effective_at` | Period in which the value applies | first instant of `2024-12` | Only from the source’s declared reference period |
| `published_at` | Official publisher release timestamp | BLS December release, 2025-01-15 08:30 ET | No; it requires the official release/schedule bound |
| `available_at` | Earliest time a consumer could retrieve the value under the source contract | max(documented release availability, first observed API capture) | **Never** set to `retrieved_at` by assumption |
| `retrieved_at` | Local capture time for this response | 2025-01-15 13:32Z in the fixture test | Yes, from the local capture clock, but it says nothing about first availability |

`first_observed_at` is retained on `TransportCapture` as a separate operational
fact. It is not a substitute for an official publication timestamp.

## Ordering contract

`validate_temporal_order` enforces the following where values are known:

```text
effective_at ≥ occurred_at
published_at ≥ effective_at
available_at ≥ published_at
retrieved_at ≥ available_at
```

The publication and availability fields may be unknown. Availability cannot be
populated without a publication bound. A missing timestamp is therefore
different from a timestamp that has been guessed. Quality checks report
missingness separately and reject impossible partial orderings.

The event constructor supplies its period as occurrence/effective time and the
release as publication time. Its validation fallback of
`available_at or published_at` is only a check input when availability is
unknown; it does not create a persisted retrieval timestamp.

## BLS availability decision

The BLS API response rows contain a reference year/period and value but do not
carry a public release/vintage timestamp. The adapter therefore accepts a
`SourceRelease` with an official `published_at` and optional source-bound
`available_at`. For an admitted row:

```text
row.available_at = max(release.available_at, capture.first_observed_at)
```

only when the release provides an availability bound. If it does not, the row
keeps `available_at = NULL`; `retrieved_at` remains the local capture time.
This avoids the false assertion `available_at = retrieved_at` and allows a
point-in-time consumer to refuse an under-specified row.

## Revision and conflict behavior

Observations are logical grains; values are append-only versions:

```text
Observation (source, series, period, dimensions)
  ├─ ObservationVersion v1 (ORIGINAL)
  └─ ObservationVersion v2 (REVISED, supersedes=v1)
```

`record_revision` requires a new version ID and a changed capture or value. It
retains both captures, times, footnotes, and the supersession link. A conflict
between two values is represented by `ObservationConflict` with both version
IDs, values, reason, and `SOURCE_CONFLICT` status. It is never silently resolved
by overwriting the earlier value.

The SQL migration carries `revision_status` and `supersedes_version_id`; an
additional conflict table preserves disagreement. The latest convenience view
is based on explicit retrieval ordering, not deletion of history.

## Unresolved vintage boundary

The current BLS API does not expose a public vintage identifier in the admitted
response. P6.5 can prove what response bytes were captured and when they were
first observed, but cannot claim that two responses are distinct official
vintages merely because their values differ. This limitation is attached to
the direct evidence and the conclusion ladder. A future source contract may
add an explicit vintage/revision identifier; it must be additive and tested.

## Point-in-time research rule

Any future historical experiment must select an observation version whose
`available_at` is no later than the decision/cutoff time, and must record when
availability is unknown. A post-cutoff retrieval cannot be relabeled as
point-in-time evidence. The current product journey demonstrates the timing
fields and limitations but does not claim a complete vintage reconstruction.
