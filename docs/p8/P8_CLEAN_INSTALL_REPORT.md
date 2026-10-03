# P8 clean-install report

## Procedure

The CI workflow and maintainer can reproduce this procedure from a clean
checkout:

```bash
python3.11 -m venv /tmp/finahinking-clean-venv
/tmp/finahinking-clean-venv/bin/python -m pip install --upgrade pip
/tmp/finahinking-clean-venv/bin/python -m pip install -e '.[dev]'
/tmp/finahinking-clean-venv/bin/python -m pytest -q
/tmp/finahinking-clean-venv/bin/python -m pip check
/tmp/finahinking-clean-venv/bin/python scripts/run_local_app.py --sample --port 18765 --smoke
```

The smoke must bind only to loopback, answer the health/home/sample routes,
and exit without an outbound source call. Its fixture labels remain
`CAPTURED`/`SAMPLE`. A real machine run should replace the placeholder paths
and record OS, Python, commit, elapsed time, and result in the release log.

## Current evidence

Source-install commands and deterministic tests are committed. A GitHub-hosted
artifact and signed native package are not claimed until the maintainer runs
the workflow on a real remote/tag.
