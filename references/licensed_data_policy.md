# Licensed Data Policy

Wind, CSMAR, Nasdaq Data Link, and JoinQuant may require account-specific permissions, field entitlements, or usage restrictions. The skill accepts only:

- an authorized API client with a secret stored outside the repository;
- a read-only authorized database connection;
- a user-provided CSV/Excel export;
- an immutable database or file snapshot with provenance.

It does not scrape licensed desktop applications, bypass access controls, infer missing entitlements, or silently replace a licensed source with a lower-quality public source. Expired, unknown, or missing authorization is an explicit `blocked`/`fallback` condition.
