"""Offline evaluation: MAE/RMSE, skill vs. persistence, and slice metrics (Phase 6).

MAPE is deliberately not used — low/near-zero gauge values make it unstable
(PLAN.md §2.4). All metrics are in centimeters, matching the `W` parameter's
native unit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SliceMetric:
    slice_name: str
    slice_value: str
    n: int
    mae_cm: float
    rmse_cm: float


@dataclass(frozen=True)
class EvaluationReport:
    model_name: str
    horizon_hours: int
    n: int
    mae_cm: float
    rmse_cm: float
    persistence_mae_cm: float
    skill_vs_persistence: float
    slices: list[SliceMetric]


def mae_cm(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse_cm(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def skill_vs_persistence(candidate_mae: float, persistence_mae: float) -> float:
    """``1 - candidate_mae / persistence_mae``; positive means candidate beats persistence."""
    if persistence_mae == 0:
        raise ValueError("persistence_mae is 0; skill is undefined")
    return 1.0 - candidate_mae / persistence_mae


def _slice_metrics(
    y_true: pd.Series, y_pred: np.ndarray, slice_name: str, slice_labels: pd.Series
) -> list[SliceMetric]:
    frame = pd.DataFrame(
        {"y_true": y_true.to_numpy(), "y_pred": y_pred, "slice": slice_labels.to_numpy()}
    )
    out = []
    for value, group in frame.groupby("slice", observed=True):
        out.append(
            SliceMetric(
                slice_name=slice_name,
                slice_value=str(value),
                n=len(group),
                mae_cm=mae_cm(group["y_true"].to_numpy(), group["y_pred"].to_numpy()),
                rmse_cm=rmse_cm(group["y_true"].to_numpy(), group["y_pred"].to_numpy()),
            )
        )
    return out


def rising_falling_slices(level_now: pd.Series, delta_1h: pd.Series) -> pd.Series:
    """Label each row 'rising', 'falling', or 'steady' from the 1h delta feature."""
    return pd.Series(
        np.where(delta_1h > 0, "rising", np.where(delta_1h < 0, "falling", "steady")),
        index=level_now.index,
        name="rising_falling",
    )


def water_level_quantile_slices(
    level_now: pd.Series, low_q: float = 0.25, high_q: float = 0.75
) -> pd.Series:
    """Label each row 'low', 'mid', or 'high' by the current level's quantile band."""
    low_cut, high_cut = level_now.quantile([low_q, high_q])
    return pd.Series(
        np.where(level_now <= low_cut, "low", np.where(level_now >= high_cut, "high", "mid")),
        index=level_now.index,
        name="level_quantile",
    )


def evaluate_predictions(
    model_name: str,
    horizon_hours: int,
    y_true: pd.Series,
    y_pred: np.ndarray,
    persistence_pred: np.ndarray,
    slice_labels: dict[str, pd.Series] | None = None,
) -> EvaluationReport:
    """Compute headline metrics plus optional named slices (e.g. season, rising/falling)."""
    if len(y_true) == 0:
        raise ValueError("cannot evaluate an empty test set")
    if not (len(y_true) == len(y_pred) == len(persistence_pred)):
        raise ValueError("y_true, y_pred, and persistence_pred must have equal length")

    y_true_arr = y_true.to_numpy(dtype=float)
    mae = mae_cm(y_true_arr, y_pred)
    rmse = rmse_cm(y_true_arr, y_pred)
    persistence_mae = mae_cm(y_true_arr, persistence_pred)

    slices: list[SliceMetric] = []
    for name, labels in (slice_labels or {}).items():
        slices += _slice_metrics(y_true, y_pred, name, labels)

    return EvaluationReport(
        model_name=model_name,
        horizon_hours=horizon_hours,
        n=len(y_true),
        mae_cm=mae,
        rmse_cm=rmse,
        persistence_mae_cm=persistence_mae,
        skill_vs_persistence=skill_vs_persistence(mae, persistence_mae),
        slices=slices,
    )
