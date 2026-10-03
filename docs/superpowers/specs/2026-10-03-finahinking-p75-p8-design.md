# Finahinking P7.5 Knowledge and P8 Public Beta Design

## Intent

The mission file for `Finahinking P7.5 + P8` is the authoritative product brief. The
goal is to turn the existing governed P7/P6.5/P6.6 research core into a useful,
local-first learning product and then prepare a reproducible open-source public
beta. The user explicitly requested autonomous execution through the P8 gate;
therefore this design treats the mission's acceptance criteria as approved scope.

## Constraints and success criteria

- Preserve P7 as the privacy, consent, provenance, and deletion boundary.
- Add one typed knowledge graph and one learning-state path; do not create a
  second personal-learning state machine.
- Make a supported local SQLite/sample-mode launch path work without credentials
  or outbound network access.
- Keep real-money trading, broker credentials, cloud accounts, telemetry, and
  automatic cloud sync out of scope.
- Verify event, knowledge, quant, strategy, personal continuity, and community
  journeys with deterministic tests and a browser/HTTP smoke surface.
- Produce the P7.5 and P8 documents and gate matrices named by the mission.
- Public-beta claims must be evidence-backed; missing signing credentials or
  remote GitHub publication must be stated rather than fabricated.

## Chosen architecture

### Knowledge engine

`finahinking.p7_5.knowledge` owns immutable typed concepts, equations,
derivations, examples, applications, misconceptions, source references, and
learning paths. A deterministic built-in curriculum is the offline seed. The
engine exposes stable IDs, prerequisite traversal, search, and a level-by-level
concept page model. It references P6.5 events and P6.6/P7 research objects by
fingerprint or typed link; it does not duplicate mastery state.

### Local product shell

The local runtime is a small standard-library HTTP service with a SQLite data
file, deterministic fixtures, semantic HTML, and no CDN dependency. The shell
owns startup, shutdown, diagnostics, and routing; domain logic remains in the
existing P6.5/P6.6/P7 modules and the knowledge engine. Routes expose Home,
Events, Knowledge, Quant, Strategy Lab, Personal, Community, and Diagnostics,
plus health/search/concept APIs. Sample data is labelled `SAMPLE` or `CAPTURED`;
live network adapters remain explicit opt-in capabilities.

### Release engineering

Source installation is the supported beta path. A GitHub Actions workflow runs
the full suite, Ruff, notebook, governance, dependency, migration, packaging,
and clean-install checks. Release metadata, contribution docs, security/license
inventory, deterministic checksums, and an explicit semver 0.x.y policy are
versioned in the repository. macOS Apple Silicon packaging is documented as a
conditional path unless a signed artifact can be built and verified in this
environment.

## Data flow and boundaries

1. First run opens SQLite and loads the deterministic knowledge/event fixtures.
2. A user follows a typed learning path or event journey.
3. Quant and strategy experiments call the existing engines and persist only
   provenance-bearing summaries through the P7 repository.
4. Personal exports remain owner-scoped and deletions revoke public projections.
5. Community views expose only explicitly consented projections and evidence
   fingerprints; private claims, API keys, and raw payloads never cross the
   boundary.

## Error and security model

Invalid IDs, expired sessions, malformed fingerprints, unsupported capabilities,
and unavailable providers return actionable, non-secret errors. All SQL remains
parameterized. No API key is logged or returned. The local service binds to
loopback by default, has no real-money endpoint, and reports network/provider
status on Diagnostics.

## Verification strategy

- Unit tests pin knowledge schema, prerequisite ordering, equations, source
  labels, and P7 deletion/privacy behavior.
- HTTP/E2E tests exercise all six required journeys and restart persistence.
- Documentation tests pin required P7.5/P8 files, gate items, public limits,
  and release links.
- Full gates run in both existing Python environments, plus Ruff, notebook,
  governance, pip, migration, package/import smoke, diff, clean worktree, and
  provenance checks.

