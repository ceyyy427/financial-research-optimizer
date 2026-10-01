from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .validation import validate_price_dataset


@dataclass(frozen=True)
class Provenance:
    provider: str
    source_url: str
    retrieved_at: datetime | None = None
    license: str = "Public source; verify current provider terms before redistribution"


@dataclass(frozen=True)
class Dataset:
    frame: pd.DataFrame
    provenance: Provenance

    def __post_init__(self) -> None:
        if self.frame.empty:
            raise ValueError("dataset cannot be empty")
        frame = self.frame.copy()
        frame.index = pd.to_datetime(frame.index)
        if frame.index.has_duplicates:
            raise ValueError("dataset contains duplicate dates")
        frame = frame.sort_index()
        frame.index.name = "date"
        if "close" in frame.columns:
            validate_price_dataset(frame, "close")
        object.__setattr__(self, "frame", frame)
