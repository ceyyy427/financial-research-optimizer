# P8.1 Performance Review

**Review date:** 2026-10-03 (Asia/Shanghai)  
**Scope:** local server-rendered product shell, its packaged launch assets, and
the static `site/index.html` launch surface.

## Review result

**PASS for the local interaction budget measured here; hosted-web performance
remains unverified.** The application has no client-side JavaScript bundle, no
remote font dependency, finite CSS-only launch motion, and small server-rendered
responses. The measurements below are loopback measurements and should not be
read as a CDN, mobile, or public-network SLA.

## Architecture decisions that protect the budget

- HTML is rendered by the existing stdlib HTTP server and the same
  `LocalApplication` object is directly testable without a browser or socket.
- There is no hydration step, JavaScript runtime, chart bundle, remote font, or
  third-party analytics request on the reviewed surfaces.
- The first launch frame is eager and dimensioned; the decorative second frame
  is `loading="lazy"` and is hidden for reduced-motion users.  Both image
  frames have width/height attributes, so the launch layout has a reserved
  aspect ratio.
- The spin/crossfade animations are finite (`18s` and `14s`, two iterations)
  and use transform/opacity rather than layout properties.  Reduced motion
  cuts the work to one near-zero-duration iteration.
- Knowledge and diagnostics are intentionally bounded local views.  The
  Workspace renderer displays at most twelve saved nodes; future unbounded
  research history should move to pagination or virtualization before it is
  treated as a large-data view.

## Reproducible loopback measurement

A Python standard-library probe created an ephemeral `ThreadingHTTPServer`,
disabled environment proxies, requested each route 31 times, discarded the
first sample, and reported the median, p95, and maximum of the remaining 30
requests.  The observed result was:

| Route | Response bytes | p50 (ms) | p95 (ms) | max (ms) |
|---|---:|---:|---:|---:|
| `/` | 17,016 | 0.446 | 0.636 | 0.928 |
| `/events` | 19,004 | 0.749 | 1.175 | 1.347 |
| `/explore` | 15,580 | 0.622 | 0.892 | 3.580 |
| `/knowledge` | 19,595 | 1.901 | 2.762 | 4.254 |
| `/knowledge/volatility` | 19,774 | 1.785 | 3.483 | 4.854 |
| `/quant` | 16,634 | 0.443 | 0.889 | 1.207 |
| `/strategy` | 16,948 | 0.445 | 0.762 | 0.864 |
| `/workspace` | 15,799 | 0.585 | 0.738 | 1.179 |
| `/community` | 16,046 | 0.707 | 1.083 | 1.254 |
| `/diagnostics` | 16,507 | 1.629 | 2.096 | 3.129 |

The probe was run with:

```text
PYTHONPATH=src .venv/bin/python <stdlib loopback benchmark>
```

It used `ProxyHandler({})`, an in-memory SQLite database, and an ephemeral
port; no external service or browser cache was involved.  This makes the
numbers reproducible as a regression check, not a claim about end-user
latency.

## Asset and package footprint

The two user-provided launch frames are optimized JPEGs and are served through
an allow-listed route:

| Asset | Dimensions | Bytes |
|---|---:|---:|
| `finathink-research-splash.jpg` | 900 × 900 | 127,715 |
| `finathink-splash-map.jpg` | 1,536 × 1,024 | 212,528 |
| **web pair** | — | **340,243** |

The same pair is present under package data so an installed wheel does not
depend on the source checkout.  There is no image processing at request time.

## Validation evidence

```text
.venv/bin/python -m py_compile src/finahinking/local_app.py  PASS
.venv/bin/ruff check src tests scripts                         PASS
.venv/bin/pytest -q (focused product/security/e2e set)          23 passed
.venv/bin/pip-audit -r requirements.lock --strict ...           No known vulnerabilities found
```

The full dual-environment suite is recorded by the P8.1 execution owner; this
review does not substitute the full release gate with a microbenchmark.

## Limitations and follow-up

- No real-device, throttled-network, Lighthouse, WebPageTest, or hosted CDN
  measurement was performed.  Static-site compression, HTTP/2/3, cache policy,
  and image delivery depend on the eventual host.
- Dynamic pages deliberately send `Cache-Control: no-store` because the local
  workspace can contain private research.  A hosted deployment must design a
  privacy-safe cache policy before enabling compression/caching.
- The static page's images are local relative assets; a missing asset should be
  surfaced by a deployment smoke test rather than silently treated as a
  successful beta.
- If research history, concept catalogs, or community rooms become large, add
  bounded queries/pagination before expanding the public surface.

