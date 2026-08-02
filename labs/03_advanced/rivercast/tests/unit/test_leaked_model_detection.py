"""Phase 6 acceptance criterion: "a deliberately leaked model is caught by
tests or review fixtures." Two layers are exercised here:

1. `train_candidate` refuses to train on a feature frame containing a
   label-shaped column (`target_level_*`) -- a real, load-bearing guard, not
   just a test assertion.
2. Even when a leak doesn't have a recognizable name (e.g. a feature that
   happens to encode the future value under an innocuous name), the
   resulting model's suspiciously perfect skill is the fixture-verified
   signal a maintainer's review would catch before promotion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rivercast.models.evaluate import evaluate_predictions
from rivercast.models.train import predict_candidate, train_candidate


def _honest_dataset(n: int = 300, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    level_t = rng.normal(loc=100, scale=10, size=n)
    noise = rng.normal(scale=5.0, size=n)
    target_level_6h = level_t + noise  # genuinely hard to predict exactly
    features = pd.DataFrame({"kaub_level_t": level_t, "kaub_lag_1h": level_t - 0.5})
    return features, pd.Series(target_level_6h, name="target_level_6h")


def test_honest_model_has_bounded_skill_not_near_perfect() -> None:
    features, labels = _honest_dataset()
    persistence_pred = features["kaub_level_t"].to_numpy()

    result = train_candidate(features, labels, "hist-gradient-boosting", horizon_hours=6)
    predictions = predict_candidate(result, features)
    report = evaluate_predictions(
        "hist-gradient-boosting", 6, labels, predictions, persistence_pred
    )
    # An honest model cannot perfectly predict pure noise it never saw.
    assert report.mae_cm > 1.0
    assert report.skill_vs_persistence < 0.99


def test_train_candidate_refuses_label_shaped_feature_column() -> None:
    """The load-bearing guard: a target_level_* column in the training
    features must stop training outright, before any fit happens.
    """
    features, labels = _honest_dataset()
    leaked_features = features.copy()
    leaked_features["target_level_6h"] = labels.to_numpy()

    with pytest.raises(ValueError, match="leakage signature"):
        train_candidate(leaked_features, labels, "hist-gradient-boosting", horizon_hours=6)


def test_unnamed_leak_produces_suspiciously_perfect_skill() -> None:
    """A leak without a recognizable column name (e.g. mislabeled during
    feature engineering) is not caught by the name-based guard, but its
    effect is: near-zero error and skill collapsing to ~1.0. That signature
    is what a maintainer's baseline-report review is looking for
    (PLAN.md Phase 6 acceptance criteria).
    """
    features, labels = _honest_dataset()
    persistence_pred = features["kaub_level_t"].to_numpy()

    leaked_features = features.copy()
    leaked_features["upstream_reading"] = labels.to_numpy()  # innocuous name, same leak

    result = train_candidate(leaked_features, labels, "hist-gradient-boosting", horizon_hours=6)
    predictions = predict_candidate(result, leaked_features)
    report = evaluate_predictions(
        "hist-gradient-boosting", 6, labels, predictions, persistence_pred
    )

    # The leaked column collapses error far below what genuine 6h-ahead
    # skill ever achieves, and the persistence baseline (which cannot see
    # the leak) does not improve -- the gap between them is the tell.
    assert report.mae_cm < 1.0, "expected the leaked model's error to collapse"
    assert report.skill_vs_persistence > 0.8, "expected suspiciously high skill from the leak"
