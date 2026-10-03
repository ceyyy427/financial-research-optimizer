# P7.5 security review

The local boundary is deliberately narrow:

- the default listener is loopback and offline; no API key is required;
- the P7 repository remains the authorization boundary and all SQL values are
  bound parameters;
- personal nodes are private by default and community projections require the
  existing explicit-consent contracts;
- JSON request bodies are bounded, malformed JSON returns an actionable 400,
  and unknown routes do not reveal filesystem details;
- HTML values are escaped; the response sends `Content-Security-Policy`,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
  `Cache-Control` headers;
- the shell exposes no broker, order, transfer, or real-money endpoint;
- provider credentials are not read by the sample path and are never written to
  diagnostics or logs.

This is a local beta review, not a hosted threat model. Before exposing a
listener beyond loopback, add authenticated transport, rate limiting, backup
encryption, abuse controls, and an independent production security review.
