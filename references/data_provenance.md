# Public data provenance protocol

## Source selection

Prefer official exchange, central-bank, regulator, or index-provider data. If the source is a public mirror, record the original provider and mirror URL separately. Use web search to verify current access and field definitions before retrieval.

## Required metadata

For every series record:

- provider and original series name;
- mirror or API URL;
- retrieval timestamp in UTC;
- start/end date and frequency;
- timezone and market calendar;
- adjusted versus unadjusted price convention;
- split/dividend/rollover treatment;
- missing and revision policy;
- usage/license note;
- local snapshot path and checksum if saved.

## Common financial-source hazards

- Yahoo-like historical endpoints may change fields, rate-limit requests, or revise adjusted values.
- Macro series can be revised; distinguish real-time vintages from latest-revised history.
- Index constituent lists can create survivorship bias.
- Futures contracts require explicit roll rules.
- Intraday data require exchange timezone, latency, and trade-condition rules.
- News and filings require publication timestamp, not only document date.
- Derived indicators must be computed within the historical window.

## Evidence language

Use “public mirror of [provider] data” when the original feed is not directly retrieved. Use “descriptive association” rather than “cause” unless an identification design supports causality. A forecast is model-implied and conditional on the sample, features, and protocol.

