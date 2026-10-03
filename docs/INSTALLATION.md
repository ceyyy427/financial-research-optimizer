# Installation

## Supported path

The validated public-beta path is a source install on Python 3.11+ using
SQLite. macOS Apple Silicon, Linux, and Windows source checkouts use the same
commands (activate the virtual environment with the platform's shell syntax).

```bash
git clone <repository-url>
cd Finahinking
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
```

No package-manager plugin, broker SDK, vector database, or external market-data
credential is required for sample mode. The lock file and
`DEPENDENCY_RECORD.md` are the dependency sources of truth.

## Optional research tools

Install `.[research]` only for the notebook workflow:

```bash
python -m pip install -e '.[dev,research]'
```

PostgreSQL is an advanced, disposable migration target and is not required for
the local app. Never put credentials in the repository; provider keys belong
in process environment/configuration and are not logged.

## Start and stop

```bash
python scripts/run_local_app.py --sample --port 8765
```

The app binds to `127.0.0.1` by default. Stop with `Ctrl-C`; user state is
stored at `~/.finahinking/finahinking.sqlite3` (override with
`FINAHINKING_DB` or `FINAHINKING_DATA_DIR`) so an ordinary code update does not
replace the database. Use the backup instructions in [PRIVACY.md](PRIVACY.md).

## Clean-install evidence

The release gate recreates a fresh virtual environment, installs from the
editable package, runs tests, and launches the sample app without network
access. See [P8_CLEAN_INSTALL_REPORT.md](p8/P8_CLEAN_INSTALL_REPORT.md).

## Troubleshooting

- `python: command not found`: install Python 3.11+ and retry.
- Dependency build failure: upgrade `pip`, then use the lock-compatible Python
  version; do not bypass the lock by adding arbitrary packages.
- Port in use: pass another local `--port`.
- Missing fixture: reinstall from a clean checkout; sample mode must not fetch
  an unreviewed replacement from the network.
- A source provider fails: inspect the diagnostics page and use captured mode;
  network failure must not silently change the provenance label.
