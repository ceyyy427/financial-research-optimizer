# P6.5 Security Review

## Scope and review posture

This is a source-and-code-bound review of the P6.5 vertical slice in this
checkout. It covers the BLS transport/capture path, canonical models, the
SQLite test repository and PostgreSQL migration, the P6 typed quant boundary,
claim/evidence construction, and the product journey. It does not certify a
deployed service, a live network perimeter, credentials, or a production
PostgreSQL operational configuration. The review deliberately records limits
instead of treating a fixture replay as a production security assertion.

The external BLS response is **untrusted data**. It is parsed as data and is
never treated as a system instruction. The LLM/product layer has no route from
source text to arbitrary SQL, shell, Python, or package installation.

## Threat model and controls

| Boundary | Implemented control | Evidence in the repository |
| --- | --- | --- |
| Source transport | The BLS client accepts one HTTPS endpoint and one host, uses bounded timeout/retries, caps the response size, records selected headers, and rejects an unallowlisted redirect. | `src/finahinking/p6_5/bls.py`; `tests/p6_5/test_bls_adapter.py` |
| Capture integrity | Request and payload SHA-256 fingerprints are recorded with retrieval and first-observed times. Raw bytes are retained before parsing and replayed offline. | `TransportCapture`, `BLSClient.capture_bytes`, `BLSClient.replay` |
| Parser boundary | Only the observed `REQUEST_SUCCEEDED`/`Results.series` grammar is admitted. Shape drift is a hard quarantine rather than a compatibility guess. | `BLSCPIAdapter.parse_capture`; schema-drift and source-failure tests |
| Untrusted text | P6 text/payload validation rejects execution directives, prompt-injection markers, arbitrary URI/location values, oversized/deep structures, and forbidden keys. | `src/finahinking/p6/security.py`; `test_security_quality_evaluation.py` |
| SQL safety | Repository statements use fixed parameterized SQL. There is no public free-form SQL or LLM-to-database path. | `src/finahinking/p6_5/repository.py`; parameterized lookup test |
| File safety | Raw artifacts use a bounded identifier, a repository-owned root, a temporary file, `fsync`, and atomic `os.replace`. | `SQLiteUnderstandingRepository.save_capture`; product capture persistence |
| Claim grounding | Verified P6 and P6.5 claims require process-local verification tokens and matching evidence fingerprints. Bundles reject unknown evidence links. | `p6/grounding.py`, `p6_5/models.py`, `p6_5/claims.py` |
| Quant authority | The event bridge emits a typed P6 request and invokes the existing `P6QuantGateway`; it does not import a quant runtime or execute generated code. | `src/finahinking/p6_5/quant_bridge.py`; `tests/p6_5/test_quant_bridge.py` |
| Product disclosure | The journey exposes evidence, limitations, unknowns, a conclusion ladder, and a grounded Predict–Reveal–Explain result. | `src/finahinking/p6_5/product.py`; `tests/p6_5/test_product_journey.py` |
| Static execution check | P6.5 source is scanned in tests for direct `eval`, `exec`, and `compile` calls. | `test_security_quality_evaluation.py` |

## Review checks

### SQL and database boundary

The repository's lookup path binds `claim_id` as a parameter; an input such as
`claim-1' OR 1=1; DROP TABLE ...` is treated as a value. The migration uses
foreign keys, check constraints, uniqueness constraints, and indexes. The
disposable verification helper (`scripts/verify_p6_5_postgres.sh`) applies the
same migration to `postgres:16-alpine` and checks required tables, foreign
keys, check constraints, and indexes.

This is a schema and query review, not a penetration test. The migration
declares the event/evidence foreign key, and the repository test verifies that
a failed link rolls back the event row before it can become an orphan.

### Prompt injection and source content

The parser never evaluates source strings. The P6 security boundary rejects
phrases that attempt to ignore policy, invoke tools, alter provenance, run
shell commands, or inject SQL/Jinja syntax. The controls are deliberately
conservative and bounded; they reduce an obvious prompt injection path but do
not prove that every natural-language attack is detected. Any future document
or browser adapter must preserve the rule that source content is data, not
authority, and must pass through an equivalent untrusted-content boundary.

### Provenance and forged verification

`source_verified=True` is not accepted from ordinary model construction: the
P6 and P6.5 models require an internal token issued by the verifier. The
product journey obtains claims through `verified_claim` and checks them in an
`EvidenceBundle`. This prevents a caller from self-attesting a fingerprint in
the normal Python API.

The database column remains a serialized boolean and cannot know about the
process-local token. Direct SQL writers, compromised process memory, or a
future repository method could therefore bypass the model invariant. Production
writes must be restricted to the repository/service boundary, and the token
check should be supplemented with a database trigger or a signed evidence
envelope before the schema is used by untrusted writers.

### Network, path, and resource limits

The BLS client has a bounded request span, series count, retries, response
bytes, and timeout. Artifact identifiers are checked against path traversal.
`BLSClient.replay` accepts a caller-provided local path; it is safe for the
trusted test operator but is not an isolation boundary for an attacker who can
choose arbitrary filesystem paths. A future service endpoint must resolve
fixtures against an allowlisted root and enforce authorization before replay.

### Dependency and capability boundary

No new plugin, MCP connector, package-manager install, or dynamic code runtime
was required for the P6.5 slice. It reuses the existing P6 gateway and the
repository's current Python environment. This review does not replace a fresh
`pip check`, lockfile/SBOM review, container scan, or secret scan.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| S-01 | Closed | Event-to-evidence links lacked a database-enforced foreign key. | Closed by the reviewed migration, repository transaction, and PostgreSQL gate. |
| S-02 | Medium | The serialized `source_verified` flag can be forged by a direct database writer. | Open; keep writes behind the verifier and add a database-level integrity mechanism in a follow-up. |
| S-03 | Low | Replay path authorization is an operator assumption, not a sandbox. | Acceptable for deterministic CI; require an allowlisted root for an exposed service. |
| S-04 | Low | Text filters cannot guarantee semantic prompt-injection detection. | Acceptable only with the typed-tool boundary and no source-derived authority. |
| S-05 | Informational | Live transport, TLS policy, rate-limit behavior, and operational secrets were not tested in CI. | Keep live smoke separate and run it under an approved operator identity. |
| S-06 | Closed | The product journey originally constructed BLS `Source`/`SourceRelease` records without an admission lookup. | Closed by resolving the capture source through the reviewed `SourceRegistry` and enforcing the admitted BLS endpoint/release URL before orchestration. |

## Review conclusion

The P6.5 fixture path has a defensible **security boundary for the current
local vertical slice**: untrusted source text is data, SQL is parameterized,
transport and artifacts are bounded, and verified claims require evidence.
It is not a claim of production security clearance. S-02 and the operational
limits above remain visible in the Gate Review and P7 readiness decision.
