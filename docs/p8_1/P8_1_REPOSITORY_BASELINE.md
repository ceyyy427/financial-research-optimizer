# P8.1 Repository Baseline

Recorded: 2026-10-03 (Asia/Shanghai)

## Local state before P8.1 changes

| Field | Observed value |
|---|---|
| Working tree | clean (`git status --branch --short` reported `## main`) |
| HEAD | `e715b289a9f118858982045800694fefb129a7b2` |
| Branch | `main`, tracking metadata absent |
| Local tag | `v0.1.0` |
| Configured remotes | none |
| Recent history | latest commit `e715b28 docs: point gates at local release tag`; preceding validated product/release commits include `4a6efc1`, `1c8ff26`, `a159c59`, `2cdda3d`, `c7d07eb` |
| Canonical URL required by mission | `https://github.com/ceyyy427/finathink.git` |

The reported starting commit was verified rather than assumed. The canonical
remote was not configured locally at baseline, so no remote mutation has yet
been inferred from local history.

## Tool/authentication baseline

- `/usr/bin/git` is available.
- `/Users/mac/.local/bin/gh` is available and authenticated as `ceyyy427` via
  the system keyring; no credential value was printed or stored.
- `.venv/bin/python`, pytest, Ruff, and pip-audit are available.
- The canonical repository responds to a read-only `git ls-remote` request;
  remote `main` currently resolves to `f0cb4b6ed282966dcc17f63e8616e6ccb004f4c5`.
- No push or fetch has been performed at the time of this baseline record.

## Safety boundary

No force push is permitted. Before any push, the canonical remote will be
configured only with the exact mission URL, fetched, classified by merge-base,
and protected with explicit safety references if reconciliation is needed.

