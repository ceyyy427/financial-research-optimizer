import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from finahinking.data.validation import validate_price_dataset


def test_validate_price_dataset_accepts_positive_prices():
    frame = pd.DataFrame({"close": [100.0, 101.0]}, index=pd.date_range("2024-01-01", periods=2, freq="D"))
    assert_frame_equal(validate_price_dataset(frame, "close"), frame)


@pytest.mark.parametrize("bad", [pd.DataFrame(), pd.DataFrame({"close": [0.0, 1.0]})])
def test_validate_price_dataset_rejects_empty_or_nonpositive(bad):
    with pytest.raises(ValueError):
        validate_price_dataset(bad, "close")


def test_validate_price_dataset_rejects_missing_column_and_unsorted_dates():
    missing = pd.DataFrame({"value": [1.0]}, index=pd.date_range("2024-01-01", periods=1))
    with pytest.raises(ValueError, match="missing required"):
        validate_price_dataset(missing, "close")
    unsorted = pd.DataFrame({"close": [100.0, 101.0]}, index=pd.to_datetime(["2024-01-02", "2024-01-01"]))
    with pytest.raises(ValueError, match="increasing"):
        validate_price_dataset(unsorted, "close")


def test_validate_price_dataset_rejects_non_datetime_or_nat_index():
    non_date = pd.DataFrame({"close": [100.0]}, index=["not-a-date"])
    with pytest.raises(ValueError, match="datetime"):
        validate_price_dataset(non_date, "close")

    nat_index = pd.DataFrame({"close": [100.0]}, index=pd.DatetimeIndex([pd.NaT]))
    with pytest.raises(ValueError, match="datetime"):
        validate_price_dataset(nat_index, "close")
