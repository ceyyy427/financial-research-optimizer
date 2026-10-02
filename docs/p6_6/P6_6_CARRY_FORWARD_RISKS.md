# P6.6 Carry-Forward Risks

P6.6 inherits these P6.5 boundaries and does not create a bypass:

- BLS vintage identification is unresolved in the admitted source slice.
- A production PostgreSQL driver/repository and migration ledger are deferred.
- Direct database writers can forge the serialized `source_verified` flag;
  Strategy Lab relies on application-level trusted records and does not add a
  new direct-writer path.
- Replay authorization and live operational controls remain service-hardening
  work; the deterministic paper fixture uses a trusted local root.
- No authoritative A-share source is admitted. Paper data must use an approved
  fixture or an explicitly admitted source.
- The P6.6 first panel experiment uses a fixed historical fixture and a
  descriptive comparison. It does not claim a live regime forecast, capacity,
  liquidity, or causal effect.

The P6.6 design adds no broker fields, broker code, live credentials, or
unbounded replay endpoint. Each risk is carried into the final security,
validity, and reproducibility reviews.
