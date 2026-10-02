# P6.5 Event Model

## Meaning

An `Event` is a source-bound thing that occurred or was published in the
world. It is not an article, an LLM summary, a market forecast, or a bag of
unattributed headlines. The event references canonical observations and
evidence; those relationships are what make the event inspectable.

## Contract

`finahinking.p6_5.models.Event` contains:

| Field | Contract |
| --- | --- |
| `event_id` | bounded stable identifier |
| `event_type` | e.g. `MACRO_RELEASE`; not a free-form source authority |
| `source_id` | admitted source FK/identity |
| `reference_period` | source period, e.g. `2024-12` |
| `occurred_at` / `effective_at` | optional explicit economic period times |
| `published_at` | required official publication time |
| `available_at` | optional source-bound consumer-availability time |
| `observation_ids` | non-empty canonical observation links |
| `evidence_ids` | non-empty direct/derived evidence links |
| `revision_status` | original/revised/superseded/unresolved revision |

The event validates temporal order and fingerprints its normalized dictionary.
It cannot be constructed without at least one observation and evidence link.

## BLS CPI event

The first event is:

```text
event type:       MACRO_RELEASE
source:           bls (U.S. Bureau of Labor Statistics)
reference period: 2024-12
publication:      official December 2024 CPI release
observations:     CUUR0000SA0 and CUSR0000SA0 rows for the period
evidence:         preserved API capture + official release document
```

The API capture may include a wider period range for fixture/replay purposes;
the event selects only the release’s reference period. Rows with a missing `-`
value or an invalid footnote are quarantined and cannot silently become event
measurements. Consensus surprise, “hot/cool” labels, and price reactions are
not event fields because they would require separately admitted sources and a
different temporal contract.

## Lifecycle

```text
admitted SourceRelease
       ↓
captured TransportCapture + immutable Artifact
       ↓
strict parser / quality report
       ↓
ObservationVersion(s)
       ↓
Event + observation/evidence links
       ↓
claims, concepts, hypothesis, quant evidence
```

At every step, the prior artifact and fingerprint remain available. A later
source revision appends a version and marks the event/observation status; it
does not rewrite an earlier event as if the historical state never existed.

## Event-to-product behavior

`UnderstandingEngine.run_cpi_journey` exposes the event progressively:

1. `what_happened` and `what_changed` identify the release and period;
2. `why_it_may_matter` shows the structured inflation/rates/yields/valuation
   mechanism and its theory limitation;
3. `show_evidence` expands source, capture, publication/availability timing,
   artifact and quant references;
4. `test_idea` binds an event-scoped question to the existing P6 typed gateway;
5. the conclusion ladder separates known facts, evidence suggestions,
   plausibility, unknowns, and view-changing evidence;
6. learning artifacts retain the same evidence and limitation references.

This ordering is progressive disclosure, not a claim that the mechanism caused
the observed index value or that the next return is predictable.
