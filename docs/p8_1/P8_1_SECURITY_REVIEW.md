# P8.1 Security Review

**Review date:** 2026-10-03 (Asia/Shanghai)  
**Threat model:** a local-first, sample/offline research application bound to
loopback. It is not an authenticated multi-user service and is not a broker,
execution, or hosted public API.

## Review result

**PASS for the reviewed local security boundary; hosted/public deployment is
not approved by this document.** The implementation rejects non-loopback Host
and Origin values, protects browser form mutations with a session-bound CSRF
token, bounds request bodies, escapes rendered user content, allow-lists image
assets, and emits restrictive browser headers. The residual risks below are
intentional consequences of the local-only model and must be closed before
turning this server into a network-facing service.

## Controls and evidence

| Area | Implementation | Evidence |
|---|---|---|
| Bind boundary | `LocalAppConfig` and `create_server` accept only `127.0.0.1`, `localhost`, or `::1`. | `tests/p7_5/test_product_gate_real.py::test_knowledge_pages_are_total_and_loopback_binding_is_enforced` |
| Host/Origin check | `_Handler._safe_origin()` rejects non-loopback Host and an Origin whose scheme/host is not loopback. | Live probe: bad Host `403`; `Origin: https://evil.invalid` `403`. |
| Browser mutation protection | URL-encoded forms require the deterministic session-bound `_csrf` value; missing/mismatched tokens return `403`. | Live probe: form without CSRF `403`; product tests exercise private mutations. |
| Body/resource bound | POST rejects invalid/negative lengths and bodies over 1,000,000 bytes with `413`. | Live probe: oversized declared body `413`. |
| Content handling | JSON is parsed with `json.loads`; malformed JSON returns `400`; form parsing uses `parse_qs`. | Live probe: invalid JSON `400`. |
| Output encoding | User-controlled titles, claims, payload details, labels, and route identifiers are passed through `html.escape` before HTML rendering. | Live probe saved `<script>alert(1)</script>` and confirmed escaped output (`HTML_ESCAPE=PASS`). |
| Asset traversal | `asset_bytes()` accepts exactly the two packaged `.jpg` names and rejects `../escape`. | Live probe: `ASSET_ALLOWLIST=PASS`. |
| Browser headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, restrictive `Permissions-Policy`, and CSP are emitted. | Live header capture on `/`. |
| CSP | `default-src 'self'`; same-origin images/connections; no scripts; form action same-origin; no framing. Inline style is allowed because the current shell embeds CSS. | Live header capture; shell has no JavaScript bundle. |
| Cookie posture | Local cookie is `HttpOnly; SameSite=Strict; Path=/`; no secret or credential is stored in source. | Live header capture and secret scan. |
| Privacy boundary | Diagnostics redacts database path and personal payloads; community projection is explicit and allow-listed. | `test_diagnostic_bundle_and_private_backup_are_redacted_and_replayable`; projection consent test. |
| Dynamic execution | Reviewed P6 gateway/source tests reject `eval`, `exec`, compile, shell/install requests, mutation payloads, and unapproved tool names. | `tests/p6/test_gate_security_and_grounding.py`, `tests/p6/test_security_and_audit.py`. |

## Reproducible gate output

The focused security/product/e2e set completed as follows:

```text
.venv/bin/pytest -q \
  tests/p7_5/test_local_app.py \
  tests/p7_5/test_product_gate_real.py \
  tests/p7_5/test_e2e.py \
  tests/p6/test_gate_security_and_grounding.py \
  tests/p6/test_security_and_audit.py
23 passed in 4.67s

.venv/bin/python scripts/secret_scan.py
secret scan passed (no known credential patterns)

.venv/bin/pip-audit -r requirements.lock --strict --progress-spinner off
No known vulnerabilities found

.venv/bin/ruff check src tests scripts
All checks passed!

git diff --check
(no output; PASS)
```

The captured response headers on `/` were:

```text
Cache-Control: no-store
Content-Security-Policy: default-src 'self'; img-src 'self'; style-src 'unsafe-inline'; script-src 'none'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Referrer-Policy: no-referrer
Set-Cookie: finahinking_session=local; HttpOnly; SameSite=Strict; Path=/
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

## Explicit residual risks

- There is no user authentication or authorization layer in this local shell;
  the fixed local cookie is a browser-hardening aid, not an identity proof.
- JSON POST requests are accepted for the loopback API without a form CSRF
  field.  They remain bounded by the loopback Host/Origin check and are useful
  for local tests/clients, but this is not a sufficient design for a hosted
  cross-origin API.  A public deployment needs authenticated sessions, strict
  origin policy, and CSRF protection for every state-changing content type.
- The server is plain HTTP on loopback.  `Secure` cookies, TLS, proxy trust,
  rate limiting, audit logging, and account/session lifecycle are intentionally
  outside the local beta boundary.
- CSP currently includes `style-src 'unsafe-inline'` because the server
  renders one inline style block.  It has `script-src 'none'`; if scripts are
  introduced, move styles to a nonce/hash or external stylesheet and tighten
  CSP before deployment.
- Dependency audit covers the checked lock file and environment, not the
  security posture of a future hosting platform or third-party GitHub Actions.
- Source links may lead to external providers; no credentials are sent by the
  reviewed shell, but a hosted product should add a link policy and external
  navigation review.

## Required pre-hosting actions

1. Re-run secret and dependency scans in the release environment and pin the
   exact artifact hash.
2. Add authenticated, least-privilege sessions and CSRF coverage for JSON and
   form mutations before exposing any route beyond loopback.
3. Add rate limits, structured security logging, TLS/proxy configuration, and
   an incident/credential-rotation procedure.
4. Re-audit CSP, external links, image supply chain, and diagnostics redaction
   after deployment configuration is known.

