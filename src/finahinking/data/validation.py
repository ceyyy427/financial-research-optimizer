import pandas as pd


def validate_price_dataset(frame: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    if frame.empty:
        raise ValueError("price dataset cannot be empty")
    if price_column not in frame.columns:
        raise ValueError(f"missing required column: {price_column}")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.isna().any():
        raise ValueError("price dates must be valid datetime values")
    values = pd.to_numeric(frame[price_column], errors="coerce")
    if values.isna().any() or (values <= 0).any():
        raise ValueError("prices must be numeric and strictly positive")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("price dates must be unique and increasing")
    return frame
