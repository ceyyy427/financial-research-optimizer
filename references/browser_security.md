# Browser and credential security

- Browser contexts are isolated; anonymous access is the default.
- Authorized contexts require explicit user authorization and are never copied into an analysis artifact.
- Cookies, localStorage, authorization headers, API keys, and response bodies are not logged by default.
- Trace and network capture use redacted headers; body capture is opt-in and must be justified by a source contract.
- API keys come from environment variables or runtime arguments, never committed files or HTML.
- Patchright does not bypass CAPTCHA, paywalls, access controls, or login requirements.
- The agent is read-only: it cannot submit orders or alter risk constraints.
- Failed access follows the declared source fallback chain and becomes `degraded` or `blocked`; it never becomes an undocumented source substitution.
