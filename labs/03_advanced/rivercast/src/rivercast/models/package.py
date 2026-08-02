"""Serialize/deserialize trained candidates and verify inference parity (Phase 6).

Acceptance criterion: "model predictions before and after serialization
match." ``save_model``/``load_model`` round-trip through joblib; callers are
expected to compare pre- and post-serialization predictions with
:func:`predictions_match` before trusting a serialized artifact (exercised in
``tests/unit/test_package.py`` and the baseline-training notebook).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
import pandas as pd


class Predictor(Protocol):
    def predict(self, features: pd.DataFrame) -> np.ndarray: ...


def save_model(model: Predictor, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)


def load_model(path: str | Path) -> Predictor:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"model artifact not found: {target}")
    return joblib.load(target)  # type: ignore[no-any-return]


def predict(model: Predictor, features: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict(features), dtype=float)


def predictions_match(a: np.ndarray, b: np.ndarray, rtol: float = 1e-9, atol: float = 1e-9) -> bool:
    return bool(np.allclose(a, b, rtol=rtol, atol=atol, equal_nan=True))
