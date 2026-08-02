"""Serialization tests: round-trip and pre/post-serialization inference parity."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rivercast.models.baseline import PersistenceModel
from rivercast.models.package import load_model, predictions_match, save_model
from rivercast.models.train import train_candidate


def test_persistence_model_roundtrip(tmp_path: Path) -> None:
    features = pd.DataFrame({"kaub_level_t": [100.0, 101.0, 99.5]})
    model = PersistenceModel("kaub_level_t").fit(features, pd.Series([0.0] * 3))
    predictions_before = model.predict(features)

    artifact = tmp_path / "persistence.joblib"
    save_model(model, artifact)
    loaded = load_model(artifact)
    predictions_after = loaded.predict(features)

    assert predictions_match(predictions_before, predictions_after)
    np.testing.assert_array_equal(predictions_before, predictions_after)


@pytest.mark.parametrize("model_name", ["ridge", "hist-gradient-boosting"])
def test_trained_candidate_roundtrip(tmp_path: Path, model_name: str) -> None:
    rng = np.random.default_rng(0)
    features = pd.DataFrame({"x1": rng.normal(size=50), "x2": rng.normal(size=50)})
    labels = pd.Series(rng.normal(size=50))
    result = train_candidate(features, labels, model_name, horizon_hours=6)
    predictions_before = result.estimator.predict(features)

    artifact = tmp_path / f"{model_name}.joblib"
    save_model(result.estimator, artifact)
    loaded = load_model(artifact)
    predictions_after = loaded.predict(features)

    assert predictions_match(predictions_before, predictions_after)


def test_load_missing_artifact_raises() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load_model("/does/not/exist.joblib")


def test_predictions_match_tolerates_nan_equal() -> None:
    a = np.array([1.0, float("nan"), 3.0])
    b = np.array([1.0, float("nan"), 3.0])
    assert predictions_match(a, b)


def test_predictions_match_detects_real_difference() -> None:
    a = np.array([1.0, 2.0])
    b = np.array([1.0, 2.1])
    assert not predictions_match(a, b)
