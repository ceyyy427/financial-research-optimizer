# P2 Gate Design — Reality Data Engine

## Success criteria

- ECB provider returns a normalized, validated dataset from a recorded fixture.
- Provenance includes provider, exact source URL, and retrieval time for live data.
- Invalid schema, duplicate dates, missing values, and non-positive prices fail closed.

## Architecture requirements

- Network access is isolated to `ECBProvider` and uses an allowlisted host.
- Dataset and provenance models are independent of provider implementation.

## Security requirements

- No credentials or user data are accepted or transmitted.
- Bounded timeout and explicit response schema checks are mandatory.

## Testing requirements

- Default tests use local fixtures and do not require network access.
- Live smoke test is opt-in and reports provider availability without weakening unit tests.

## Documentation requirements

- `DATA_SOURCE_EVALUATION.md` records availability, terms, reliability, maintenance, and cost.

## Limitations

- This phase does not provide a portfolio database or historical caching service.
- ECB data is not a substitute for all asset classes or trading venues.
