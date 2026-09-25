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
