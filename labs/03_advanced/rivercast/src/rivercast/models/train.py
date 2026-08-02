"""Train candidate models (PLAN.md §2.4 and Phase 6).

Two candidates beyond persistence: ``ridge`` and ``hist-gradient-boosting``.
Both are seeded for reproducibility and fit **only** on the training split —
callers must never pass validation/test rows here (enforced by the caller
contract, not re-checked internally, since this function has no way to know
which rows came from which split once handed a single frame).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ModelName = Literal["ridge", "hist-gradient-boosting"]

DEFAULT_SEED = 42


@dataclass(frozen=True)
class TrainResult:
    model_name: ModelName
    horizon_hours: int
    feature_columns: list[str]
    estimator: Pipeline
    params: dict[str, object]
    seed: int


def _build_estimator(model_name: ModelName, seed: int) -> Pipeline:
    if model_name == "ridge":
        # Ridge needs neither NaN nor unscaled inputs; the imputer and scaler
        # are fit on exactly the data passed to Pipeline.fit() -- i.e. the
        # training split only, never validation/test -- so this stays inside
        # the "fit preprocessing on the training window only" rule.
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0, random_state=seed)),
            ]
        )
    if model_name == "hist-gradient-boosting":
        # Tree-based: no scaling needed, and NaN is handled natively (matches
        # the missingness semantics of build_features()).
        return Pipeline(
            [
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=200, max_depth=6, learning_rate=0.05, random_state=seed
                    ),
                )
            ]
        )
    raise ValueError(f"unknown model {model_name!r}; expected 'ridge' or 'hist-gradient-boosting'")


def train_candidate(
    train_features: pd.DataFrame,
    train_labels: pd.Series,
    model_name: ModelName,
    horizon_hours: int,
    seed: int = DEFAULT_SEED,
) -> TrainResult:
    """Fit one candidate on the training split only.

    ``train_labels`` must already be NaN-free (see
    ``processing.dataset.training_rows``); rows with a missing label must
    never reach this function.
    """
    if train_labels.isna().any():
        raise ValueError(
            "train_labels contains NaN; filter with processing.dataset.training_rows() first"
        )
    if not train_features.index.equals(train_labels.index):
        raise ValueError("train_features and train_labels must share the exact same index")
    label_like_columns = [c for c in train_features.columns if c.startswith("target_level")]
    if label_like_columns:
        raise ValueError(
            f"train_features contains label-shaped column(s) {label_like_columns}; "
            "this is a leakage signature, refusing to train"
        )

    estimator = _build_estimator(model_name, seed)
    estimator.fit(train_features, train_labels.to_numpy(dtype=float))

    params: dict[str, object] = {
        "seed": seed,
        **{f"model__{k}": v for k, v in estimator.named_steps["model"].get_params().items()},
    }
    return TrainResult(
        model_name=model_name,
        horizon_hours=horizon_hours,
        feature_columns=list(train_features.columns),
        estimator=estimator,
        params=params,
        seed=seed,
    )


def predict_candidate(result: TrainResult, features: pd.DataFrame) -> np.ndarray:
    aligned = features[result.feature_columns]
    return np.asarray(result.estimator.predict(aligned), dtype=float)
