"""Persistence baseline tests."""

import pandas as pd
import pytest

from rivercast.models.baseline import PersistenceModel


def test_persistence_predicts_current_level_unchanged() -> None:
    features = pd.DataFrame({"kaub_level_t": [100.0, 101.0, 99.5]})
    model = PersistenceModel("kaub_level_t").fit(features, pd.Series([0.0, 0.0, 0.0]))
    predictions = model.predict(features)
    assert list(predictions) == [100.0, 101.0, 99.5]


def test_missing_level_column_raises_on_fit_and_predict() -> None:
    features = pd.DataFrame({"other_col": [1.0]})
    model = PersistenceModel("kaub_level_t")
    with pytest.raises(ValueError, match="not present"):
        model.fit(features, pd.Series([0.0]))
    with pytest.raises(ValueError, match="not present"):
        model.predict(features)
