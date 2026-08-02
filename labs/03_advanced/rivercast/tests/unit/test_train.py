"""Model training tests: reproducibility, fit-on-train-only, seed sensitivity."""

import numpy as np
import pandas as pd
import pytest

from rivercast.models.train import predict_candidate, train_candidate


def _synthetic(n: int = 200, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = 2.0 * x1 - 1.5 * x2 + rng.normal(scale=0.1, size=n)
    features = pd.DataFrame({"x1": x1, "x2": x2})
    labels = pd.Series(y, name="target_level_6h")
    return features, labels


@pytest.mark.parametrize("model_name", ["ridge", "hist-gradient-boosting"])
def test_train_and_predict_shapes(model_name: str) -> None:
    features, labels = _synthetic()
    result = train_candidate(features, labels, model_name, horizon_hours=6)
    predictions = predict_candidate(result, features)
    assert predictions.shape == (len(features),)
    assert result.feature_columns == ["x1", "x2"]
    assert result.horizon_hours == 6


def test_ridge_recovers_linear_relationship_reasonably_well() -> None:
    features, labels = _synthetic(n=500)
    result = train_candidate(features, labels, "ridge", horizon_hours=6)
    predictions = predict_candidate(result, features)
    mae = float(np.mean(np.abs(predictions - labels.to_numpy())))
    assert mae < 0.5  # noise scale is 0.1; a reasonable fit should track it


def test_same_seed_reproducible() -> None:
    features, labels = _synthetic()
    first = train_candidate(features, labels, "hist-gradient-boosting", 6, seed=7)
    second = train_candidate(features, labels, "hist-gradient-boosting", 6, seed=7)
    np.testing.assert_array_equal(
        predict_candidate(first, features), predict_candidate(second, features)
    )


def test_seed_is_recorded_and_propagated_to_the_estimator() -> None:
    features, labels = _synthetic()
    result = train_candidate(features, labels, "hist-gradient-boosting", 6, seed=7)
    assert result.seed == 7
    assert result.estimator.named_steps["model"].random_state == 7


def test_nan_labels_rejected() -> None:
    features, labels = _synthetic(n=10)
    labels.iloc[0] = float("nan")
    with pytest.raises(ValueError, match="training_rows"):
        train_candidate(features, labels, "ridge", horizon_hours=6)


def test_mismatched_index_rejected() -> None:
    features, labels = _synthetic(n=10)
    labels = labels.reset_index(drop=True)
    labels.index = labels.index + 1000
    with pytest.raises(ValueError, match="exact same index"):
        train_candidate(features, labels, "ridge", horizon_hours=6)


def test_unknown_model_name_rejected() -> None:
    features, labels = _synthetic(n=10)
    with pytest.raises(ValueError, match="unknown model"):
        train_candidate(features, labels, "random-forest", horizon_hours=6)  # type: ignore[arg-type]


def test_hist_gradient_boosting_handles_nan_features_natively() -> None:
    features = pd.DataFrame({"x1": [1.0, float("nan"), 3.0, 4.0] * 20})
    labels = pd.Series([1.0, 2.0, 3.0, 4.0] * 20)
    result = train_candidate(features, labels, "hist-gradient-boosting", horizon_hours=6)
    predictions = predict_candidate(result, features)
    assert not np.isnan(predictions).any()


def test_ridge_imputes_nan_features_instead_of_erroring() -> None:
    features = pd.DataFrame({"x1": [1.0, float("nan"), 3.0, 4.0] * 20})
    labels = pd.Series([1.0, 2.0, 3.0, 4.0] * 20)
    result = train_candidate(features, labels, "ridge", horizon_hours=6)
    predictions = predict_candidate(result, features)
    assert not np.isnan(predictions).any()
