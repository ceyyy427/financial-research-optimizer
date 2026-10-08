# Finathink research capability acceptance matrix

更新时间：2026-10-08

This is the frozen Task 1 baseline for the research-capability expansion. It
describes evidence available from the local, deterministic test suite and
release checklists. `OFFLINE_PASS` means the governed local path is tested;
`ISOLATED_DEFERRED` means an optional engine remains behind its admission
gates; `EXTERNAL_UNVERIFIED` means a real provider, connection, or browser
runtime has not been established; and `NOT_IN_SCOPE` is a permanent boundary
for this plan. Neither deferred nor unverified evidence is a pass.

| Capability | Status | Offline implementation | Isolated only | External unverified | Not in scope | Follow-up tasks |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Provider adapters | `EXTERNAL_UNVERIFIED` | Yes | No | Yes | No | 2, 3 |
| Codex/model handoff | `OFFLINE_PASS` | Yes | No | No | No | 4 |
| Factor proposal and evaluation | `OFFLINE_PASS` | Yes | No | No | No | 5, 6, 7 |
| Optional quant engines | `ISOLATED_DEFERRED` | Yes (fallback) | Yes | No | No | 8, 9 |
| Risk gates | `OFFLINE_PASS` | Yes | No | No | No | 10 |
| Paper portfolio | `OFFLINE_PASS` | Yes | No | No | No | 11 |
| Learning proposals | `OFFLINE_PASS` | Yes | No | No | No | 12 |
| Durable queue and limits | `OFFLINE_PASS` | Yes | No | No | No | 13, 14 |
| Read-only UI/report surface | `EXTERNAL_UNVERIFIED` | Yes | No | Yes (browser render) | No | 15, 16 |
| Data-vendor SDKs | `NOT_IN_SCOPE` | No | No | No | Yes | — |
| Unattended self-improvement | `NOT_IN_SCOPE` | No | No | No | Yes | — |

The machine-readable source is
`finahinking.research.release_matrix.load_release_matrix()`. It consumes the
existing runtime release checklists and points to the focused tests that
support each local claim. The matrix intentionally does not claim a named
vendor, broker, account, order, live-trading service, or autonomous code
modification loop.

Global boundaries remain unchanged: research-only, paper-only, offline-first,
no secrets or raw provider objects in artifacts, and no vendor SDK admission
without an independently trusted sandbox and explicit human review.
