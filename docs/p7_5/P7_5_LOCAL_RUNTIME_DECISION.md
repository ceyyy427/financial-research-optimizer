# P7.5 local runtime decision

Decision: ship an offline-first Python local runtime for the beta. The default
path is `python scripts/run_local_app.py` (or the installed `finahinking`
entrypoint), bound to loopback with SQLite and a deterministic sample fixture.
The shell uses the existing P7 repository for private continuity; it does not
create a second domain store.

## Boundary

- The stdlib `http.server` owns startup, shutdown, request limits, and headers.
- P6.5 owns the captured BLS CPI event and quant bridge; P6.6 remains the
  strategy research authority.
- P7 owns personal graph, history, mastery, and consented projections.
- P7.5 knowledge is read-only reference data in `p7_5.knowledge` and links to
  these existing artifacts rather than copying their state.
- There is no broker adapter, order endpoint, account credential, or
  real-money execution path.

SQLite is the default because it is portable, inspectable, and already covered
by the P7 migration. PostgreSQL remains the advanced deployment target. A
provider may be enabled only by an explicit adapter decision; the default
sample path makes no network call.

## Supported launch paths

```text
python scripts/run_local_app.py
python -m pip install -e .
finahinking
```

The default database is a user-local file at `~/.finahinking/finahinking.sqlite3`
for restart/reopen continuity; set `FINAHINKING_DB` or
`FINAHINKING_DATA_DIR` to relocate it. `FINAHINKING_HOST` and
`FINAHINKING_PORT` change the listener; `FINAHINKING_OFFLINE=1` and
`FINAHINKING_SAMPLE=1` are the safe defaults.
