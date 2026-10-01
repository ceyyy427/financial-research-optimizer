# P1 Gate Design — Research Environment

## Success criteria

- A clean Python 3.11+ environment installs the package and pinned tooling.
- `finahinking` imports with a stable version and exposes no P4 persistence
  API.
- The starter notebook executes locally with a fixed seed and no network
  dependency.
- Make targets provide repeatable install, test, lint, notebook, and gate
  commands.

## Architecture requirements

- Runtime dependencies remain limited to pandas and numpy.
- Development and notebook tooling is declared in `pyproject.toml` and
  represented by `requirements.lock`.
- Notebook examples consume package APIs rather than implementing provider
  networking or persistence.

## Security and reproducibility requirements

- No secrets, credentials, or external URLs are needed for the default gate.
- The lockfile must not contain a machine-specific editable path.
- Random examples use an explicit seed and stable assertions.

## Testing requirements

- Environment tests inspect metadata, imports, lockfile pins, notebook metadata,
  and Makefile targets.
- `make p1-gate` runs tests, lint, and deterministic notebook execution.
- The complete suite remains offline by default.

## Limitations

P1 establishes the development and notebook workflow only. It does not add
provider networking, experiment persistence, backtesting, trading automation,
or investment advice.
