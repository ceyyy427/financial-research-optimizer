# Patchright and CDP capability contract

Patchright answers how an authorized, isolated browser context is reached;
CDP answers what the browser actually emitted. Python parsers and provenance
remain the only path into canonical financial observations.

The runtime supports launch and `connect_over_cdp` modes, records browser
version and context/page status, and can reattach after a transport failure.
`CdpObserver` enables Network/Page domains best-effort, records request and
response metadata, waits for `Network.loadingFinished` before calling
`Network.getResponseBody`, and stores body bytes as separate raw files. The
network manifest contains hashes and file paths, never inline body text.

Popups and additional pages are visible through the context page collection;
iframes remain page-owned browsing targets and must be captured with explicit
frame URLs before parsing. Downloads use the existing download manager and
must be hashed into the provenance manifest. A browser crash is a degraded or
blocked acquisition event until `recover()` succeeds; it never authorizes a
silent switch to an unverified page number.
