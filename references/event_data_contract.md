# Event data contract

News, filings, macro releases, central-bank events, and earnings events follow:

```text
raw_event → normalized_event → timestamp audit → point-in-time event feature
```

Each event records occurrence, publication/release, retrieval, first-visible timestamps, source reliability, revision relationship, duplicate group, and impact window. `first_visible_at` must not precede `published_at`; a feature at forecast origin may only use events with `first_visible_at <= forecast_origin`. Duplicate or follow-up reporting is retained but grouped and must not be counted as independent evidence.

Sentiment is not a model feature by default. It must first pass the same source, timestamp, revision, and availability audit as a numerical series.
