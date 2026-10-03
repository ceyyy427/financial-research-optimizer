# C — Product architecture review

PASS. The local shell owns lifecycle, routes, diagnostics, and safe errors;
P6.5/P6.6/P7 remain the domain authorities. SQLite uses the existing P7
repository and migrations; no second personal state store was introduced.
