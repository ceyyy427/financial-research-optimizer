# P7 Research History

Research history is a private, append-only index over P6.5 evidence and P6.6
strategy/quant runs. Each entry records source kind/id, source fingerprint,
event type, title, occurred-at timestamp, and limitations. The index is a
navigation layer, not a second source of truth.

A history entry can be reopened to its immutable artifact and provenance. A
current fingerprint is required before a projection may be published; if the
underlying artifact changes, the projection becomes `STALE` and requires a
new explicit consent decision. Export is owner-scoped and excludes sessions,
other principals, and internal audit details.
