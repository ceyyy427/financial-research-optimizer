# Patchright and CDP contract

Patchright is the optional browser-access layer. It handles dynamic pages, isolated contexts, authorized sessions, downloads, screenshots, and traces. CDP is the observation layer for Chromium network, page, runtime, target, storage, fetch, performance, and tracing facts. Neither layer decides whether data are valid or whether a model is selected.

Use `scripts/browser/patchright_runtime.py` with one of `anonymous_context`, `authorized_context`, or `research_context`. Authorized storage is opt-in and isolated. `scripts/browser/cdp_session.py` and `network_capture.py` record request IDs, URLs, methods, status, redacted header hashes, content type, body hash, page URL, source ID, and retrieval time. Body capture is disabled by default.

The browser path is a fallback after an official API or download path. A page's displayed number is never a canonical observation until it passes the transformation, unit, timestamp, source, and point-in-time contracts.

Optional runtime dependency:

```bash
python3 -m pip install 'financial-research-optimizer[browser]'
```

The default CI and offline tests do not install or launch a browser.
