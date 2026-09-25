# Java/MyBatis data layer

## Decision: keep the mathematics, add the data layer

`references/model_derivations.md` is core and should be kept. It governs the estimand, assumptions, objective, gradients or first-order conditions, diagnostics, and the meaning of every model output. Removing it would make the Skill able to move data but unable to justify whether an ARMA/GARCH, Bayesian, LSTM, Transformer, or portfolio result is correctly specified.

Java/MyBatis is an optional data-access layer before feature construction. It does not replace Python/R model fitting and it must not put forecasting logic inside SQL. Use it when the source data already lives in a relational database, when an enterprise service needs a controlled read path, or when provenance and point-in-time retrieval must be enforced centrally.

```text
official/API source -> Java/MyBatis read adapter -> raw snapshot
                                  -> canonical observations -> audit/provenance
                                  -> feature/label export -> statistical/deep model
                                  -> forecast ledger -> HTML + decision table
```

## Canonical observation contract

Use a long, time-indexed observation table rather than a wide table with ambiguous dates. A minimum PostgreSQL-like schema is:

```sql
CREATE TABLE market_observation (
    observation_id  BIGSERIAL PRIMARY KEY,
    instrument_id   VARCHAR(64) NOT NULL,
    observation_ts  TIMESTAMPTZ NOT NULL,
    open_price      NUMERIC(20, 8),
    high_price      NUMERIC(20, 8),
    low_price       NUMERIC(20, 8),
    close_price     NUMERIC(20, 8),
    volume          NUMERIC(30, 8),
    adjustment_code VARCHAR(32) NOT NULL,
    source_id       VARCHAR(128) NOT NULL,
    retrieved_at    TIMESTAMPTZ NOT NULL,
    revision_id     VARCHAR(128),
    UNIQUE (instrument_id, observation_ts, adjustment_code, source_id, revision_id)
);

CREATE INDEX market_observation_lookup
    ON market_observation (instrument_id, observation_ts);
```

The exact DDL may vary by database. Preserve the semantic fields even when the source has different names. `observation_ts` is the time at which the value is observable in the market calendar; `retrieved_at` is when the adapter obtained it. They are not interchangeable.

## Java type and mapper example

Use `BigDecimal` for prices and quantities and `OffsetDateTime` for timestamps. Do not deserialize prices into binary floating-point types in the ingestion layer.

```java
package example.finance.data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

public record MarketObservation(
    String instrumentId,
    OffsetDateTime observationTs,
    BigDecimal openPrice,
    BigDecimal highPrice,
    BigDecimal lowPrice,
    BigDecimal closePrice,
    BigDecimal volume,
    String adjustmentCode,
    String sourceId,
    OffsetDateTime retrievedAt,
    String revisionId
) {}
```

```java
package example.finance.data;

import org.apache.ibatis.annotations.Param;
import java.time.OffsetDateTime;
import java.util.List;

public interface MarketObservationMapper {
    List<MarketObservation> selectWindow(
        @Param("instrumentId") String instrumentId,
        @Param("from") OffsetDateTime from,
        @Param("to") OffsetDateTime to,
        @Param("sourceId") String sourceId);
}
```

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper
  PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "https://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="example.finance.data.MarketObservationMapper">
  <resultMap id="MarketObservationMap" type="example.finance.data.MarketObservation">
    <result property="instrumentId" column="instrument_id" />
    <result property="observationTs" column="observation_ts" jdbcType="TIMESTAMP_WITH_TIMEZONE" />
    <result property="openPrice" column="open_price" jdbcType="DECIMAL" />
    <result property="highPrice" column="high_price" jdbcType="DECIMAL" />
    <result property="lowPrice" column="low_price" jdbcType="DECIMAL" />
    <result property="closePrice" column="close_price" jdbcType="DECIMAL" />
    <result property="volume" column="volume" jdbcType="DECIMAL" />
    <result property="adjustmentCode" column="adjustment_code" />
    <result property="sourceId" column="source_id" />
    <result property="retrievedAt" column="retrieved_at" jdbcType="TIMESTAMP_WITH_TIMEZONE" />
    <result property="revisionId" column="revision_id" />
  </resultMap>

  <select id="selectWindow" resultMap="MarketObservationMap">
    SELECT instrument_id, observation_ts, open_price, high_price,
           low_price, close_price, volume, adjustment_code,
           source_id, retrieved_at, revision_id
    FROM market_observation
    WHERE instrument_id = #{instrumentId}
      AND observation_ts &gt;= #{from}
      AND observation_ts &lt; #{to}
      AND source_id = #{sourceId}
    ORDER BY observation_ts ASC
  </select>
</mapper>
```

Use `#{...}` for values. Never use `${...}` for user-provided values. If a table or column name must be dynamic, select it from a hard-coded allowlist before constructing the statement.

## Read-to-analysis handoff

The Java service should export a raw snapshot or canonical Parquet/CSV plus a provenance manifest, not only an in-memory list. The handoff record must include:

- query name and mapper version;
- instrument IDs, inclusive/exclusive time bounds, timezone, market calendar;
- source ID, adjustment code, revision ID, retrieval timestamp;
- row count, duplicate count, missingness, min/max timestamp, and checksum;
- database schema version and application commit;
- whether the query is point-in-time safe and whether the source can revise history.

Then apply the normal Skill stages: audit the export, build features and labels only inside training windows, read `model_derivations.md` for every fitted model, and generate `analysis.json` with `evidence_refs` pointing to the snapshot and query IDs.

## MyBatis-specific safeguards

- Prefer a read-only database account and a read-only transaction for research retrieval.
- Bound every time-window query; add a row or page limit for high-frequency data.
- Keep SQL responsible for filtering, ordering, projection, and stable joins—not rolling statistics, labels, or model selection.
- Never join a revised fundamental or macro value to an earlier market date unless the release timestamp makes it observable at that date.
- For corporate actions, store the adjustment convention and do not mix adjusted and raw prices in one feature table.
- Avoid N+1 queries; retrieve a complete ordered window and validate its grain after mapping.
- Do not commit JDBC URLs, passwords, API tokens, production hostnames, or personal data. Use environment variables or a secret manager reference.
- Treat mapper output as untrusted until the Python/R audit confirms ordering, duplicates, gaps, units, and point-in-time availability.

## When not to add MyBatis

Do not add a Java layer when the user supplied a small CSV/Parquet snapshot, when the authoritative source already has a documented API connector, or when adding a service would make the result less reproducible. In those cases, record the direct file/API provenance and keep the pipeline simpler.

