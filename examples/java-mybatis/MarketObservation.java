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
