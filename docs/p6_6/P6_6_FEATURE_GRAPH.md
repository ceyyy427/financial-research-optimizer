# P6.6 Feature Graph

The graph is a content-addressed directed acyclic graph of feature versions.
Each node records its feature version, input node IDs, and an explanation. The
graph fingerprint covers node order, edges, feature fingerprints, and output
IDs.

The first graph is:

```text
close + available_at
        ├── lagged 20-day momentum
        └── lagged 20-day realized volatility
lagged momentum + low-volatility threshold
        ↓
cross-sectional rank / selection
        ↓
target weights
```

The second graph is:

```text
close + available_at → lagged moving average → trend condition → target weight
```

Graph validation rejects cycles, missing input nodes, duplicate IDs, unknown
feature versions, and output nodes that are not registered. The graph is used
for lineage, code explanation, debugging, education, and fingerprints.
