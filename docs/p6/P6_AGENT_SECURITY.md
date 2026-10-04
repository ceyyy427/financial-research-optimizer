# P6 Agent Security

P6 treats user prompts, retrieved text, datasets, evidence, and external
documents as untrusted data. Application policy and the fixed tool registry
are the only authorities for tool access.

The security boundary must reject attempts to execute arbitrary Python or
shell, call `eval`/`exec`, import a module, install a package, edit source,
delete artifacts, rewrite provenance, bypass the typed gateway, name an
unapproved adapter, fetch an arbitrary path or URL, or change a historical
research record. Rejection occurs before service dispatch and leaves no run or
artifact behind. Error messages are bounded and contain no source or secrets.

Tests include prompt-shaped strings in questions, assumptions, imported
evidence, tool names, and nested JSON; all are data and cannot grant
authority. Tests also verify unknown/deferred tools, callable values, path
values, mutable payloads, and forged fingerprints. There is no generated code,
shell escape, dynamic import, package manager call, or unrestricted model
agent in the P6 package.

Audit records contain the request, policy decision, tool, IDs, fingerprints,
warnings, limitations, and status. They are append-only and inspectable through
`quant.inspect_run`; security failures cannot mutate or erase previous evidence.
