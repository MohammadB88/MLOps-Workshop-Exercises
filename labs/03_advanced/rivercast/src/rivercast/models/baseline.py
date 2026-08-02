"""Persistence baseline: ŷ(t+h) = level(t) (PLAN.md §2.4 and Phase 6).

Every candidate must be compared against this. It has no parameters to fit —
"training" is a no-op — but implements the same predict-from-feature-row
interface as the trained candidates so both can flow through one evaluation
path.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class PersistenceModel:
    """Predicts the target's current level unchanged at every horizon."""

    def __init__(self, level_column: str) -> None:
        self.level_column = level_column

    def fit(self, features: pd.DataFrame, labels: pd.Series) -> PersistenceModel:
        if self.level_column not in features.columns:
            raise ValueError(f"level column {self.level_column!r} not present in features")
        return self  # no parameters; kept for interface parity with trained models

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        if self.level_column not in features.columns:
            raise ValueError(f"level column {self.level_column!r} not present in features")
        return features[self.level_column].to_numpy(dtype=float)
