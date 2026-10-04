# Strategy Research Constitution

1. A strategy is a research artifact with an explicit hypothesis, data
   lineage, feature definitions, timing, costs, validation design, and
   limitations.
2. Backtest performance is historical evidence. Paper simulation is forward
   research evidence. Neither is a guarantee of future returns.
3. A user idea must become a typed, reviewable `StrategySpec` before any
   compiler or backtest receives it. Material assumptions are shown rather than
   silently changed.
4. Features are versioned, fingerprinted, point-in-time checked, and linked to
   the strategy and its educational explanation.
5. Strategy IR is the only executable representation. It contains registered
   primitives and JSON-safe parameters, never arbitrary Python, shell, network,
   database, or broker operations.
6. Educational code is an export for reading and learning. It is statically
   scanned and never automatically executed by Finathink.
7. Costs, slippage, turnover, cash, benchmark, and risk limits are explicit.
   A high metric does not justify calling a strategy good.
8. Parameter variation records its search space, experiment count, selection
   method, frozen boundary, and OOS result. Automated cherry-picking is not a
   product feature.
9. Paper simulation uses a frozen `StrategyVersion`, approved data, a virtual
   clock, and virtual fills. It has no broker identity, credential, real cash,
   or real order path.
10. Exports preserve StrategyVersion, FeatureVersions, dataset fingerprints,
    ResearchRun/QuantRun references, code commit, dependencies, assumptions,
    limitations, and an artifact fingerprint.
11. The user remains responsible for any use outside Finathink. Finathink ends
    at research, learning, simulation, and export.
