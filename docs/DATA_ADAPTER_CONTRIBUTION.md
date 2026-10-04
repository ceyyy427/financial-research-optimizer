# Data-adapter contribution contract

New adapters pass Source Admission before implementation is merged:

1. identify the official endpoint, owner, terms, license/reuse basis, and
   attribution requirement;
2. constrain hosts, redirects, methods, timeouts, payload sizes, retries, and
   request parameters;
3. define temporal semantics, publication/retrieval times, revisions, missing
   values, and point-in-time limitations;
4. preserve request fingerprint, payload hash, parser version, source status,
   and capture/replay metadata;
5. add deterministic fixtures and admission/quarantine tests, including a
   network-failure path that cannot silently become fresh data;
6. document API keys, outbound calls, rate limits, and user-visible labels.

Do not bundle proprietary data, credentials, or a provider SDK merely for
convenience. A live adapter is optional; sample mode must remain offline.
