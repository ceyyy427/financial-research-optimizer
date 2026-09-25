# Public data provenance protocol

## Source selection

Prefer official exchange, central-bank, regulator, or index-provider data. If the source is a public mirror, record the original provider and mirror URL separately. Use web search to verify current access and field definitions before retrieval.

## Source routing for common Chinese and global websites

Use the following routing table as a starting point. It is a source-selection aid, not permission to bypass authentication, paywalls, robots rules, rate limits, or terms of use.

| Research need | Preferred source | Secondary source / connector | Required audit note |
|---|---|---|---|
| China GDP, CPI, PPI, PMI, population, property, consumption | [National Data](https://data.stats.gov.cn/) | public statistical releases | release date, vintage/revision, unit, frequency, seasonal adjustment |
| China money, credit, rates, financial conditions | [People's Bank of China](https://www.pbc.gov.cn/) | official bulletin or public statistical series | announcement timestamp, policy versus realized value, revision status |
| China listed-company filings and financials | [CNINFO](https://www.cninfo.com.cn/) | SSE/SZSE filing pages | announcement time, fiscal period, restatement, consolidated scope |
| Shanghai / Shenzhen exchange prices and notices | [SSE](https://www.sse.com.cn/) / [SZSE](https://www.szse.cn/) | licensed market-data provider | trading calendar, adjustment, suspension, corporate action |
| China daily market lookup | [Eastmoney](https://www.eastmoney.com/) / [10jqka](https://www.10jqka.com.cn/) | AkShare, Tushare, JoinQuant when authorized | public mirror versus original provider, timestamp, adjusted/unadjusted flag |
| China institution-grade or academic panel | [Wind](https://www.wind.com.cn/) / [CSMAR](https://www.gtarsc.com/) | authorized export/API only | license, query definition, vintage and survivorship rules |
| US/global macro time series | [FRED](https://fred.stlouisfed.org/) | FRED API, Nasdaq Data Link | series ID, realtime_start/realtime_end, revision vintage, units |
| US company filings | [SEC EDGAR](https://www.sec.gov/edgar) | SEC submissions/XBRL APIs | filing accession, filing timestamp, XBRL taxonomy, restatement |
| US/global exchange data | [NYSE Data Products](https://www.nyse.com/data-products) | licensed feed, Yahoo Finance | exchange timezone, entitlements, corporate actions, delayed/live status |
| broad global market lookup | [Yahoo Finance](https://finance.yahoo.com/) / [Investing.com](https://www.investing.com/) / [TradingView](https://www.tradingview.com/) | documented public API or authorized connector | source is a public mirror/aggregator unless original provenance is explicit |

When a connector such as AkShare, Tushare, JoinQuant, FRED API, SEC EDGAR API, Nasdaq Data Link, Alpha Vantage, EODHD, or Polygon.io is used, store both the connector endpoint and the underlying provider. The connector is not automatically the authoritative source.

### Connector entry points

| Connector | Typical use | Minimum provenance fields |
|---|---|---|
| [AkShare](https://akshare.akfamily.xyz/) | China/global public-data adapters | function name, upstream provider, query date, adjustment |
| [Tushare](https://tushare.pro/) | China market and fundamentals | token/account authorization, API endpoint, fields, quota/date |
| [JoinQuant](https://www.joinquant.com/) | China research datasets | authorized account, query code, point-in-time rules, license |
| [FRED API](https://fred.stlouisfed.org/docs/api/fred/) | macro series and vintages | series ID, API query, realtime dates, units |
| [SEC EDGAR API](https://www.sec.gov/edgar/sec-api-documentation) | filings and XBRL | CIK, accession, user-agent, filing timestamp |
| [Nasdaq Data Link](https://data.nasdaq.com/) | market, macro, alternative data | dataset code, query, license, revision policy |
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | global market and indicators | endpoint, symbol, interval, adjusted flag, rate limit |
| [EODHD](https://eodhd.com/financial-apis/) | end-of-day and fundamentals | endpoint, exchange code, corporate-action convention |
| [Polygon](https://polygon.io/docs) | US/global market and aggregates | endpoint, ticker, timezone, entitlement, delayed/live status |

Never put API tokens in the Skill, generated HTML, GitHub commits, logs, or provenance JSON. Record an environment-variable name or secret reference instead.

### Source selection algorithm

1. Map the target field to the routing table by geography, asset class, frequency, and legal access.
2. Choose the highest available source tier: official/regulator/exchange, documented API, licensed database, public aggregator.
3. Verify field definition, time zone, adjustment convention, revision policy, and retrieval timestamp.
4. If the preferred source is unavailable, use the next tier only when the original provider or limitation is recorded.
5. Cross-check a material series against one independent source when feasible; report discrepancies rather than averaging silently.
6. Save the exact URL, query parameters or series ID, response timestamp, and snapshot checksum in the provenance record.

### Adaptation boundaries

- Do not scrape an interactive page when an official downloadable file or documented API exists.
- Do not infer historical availability from a current page; confirm the series dates and release timestamps.
- Do not use Wind, CSMAR, JoinQuant, or other paid/authenticated sources without a user-provided authorized connection or export.
- Do not treat a chart value from Eastmoney, 10jqka, Investing.com, or TradingView as an audited raw series until fields, adjustments, and timestamp semantics are confirmed.
- For news, announcements, and filings, use publication time as the information timestamp; document date alone is insufficient.

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
