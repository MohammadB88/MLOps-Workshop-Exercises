from rivercast.models.baseline import PersistenceModel
from rivercast.models.evaluate import (
    EvaluationReport,
    SliceMetric,
    evaluate_predictions,
    rising_falling_slices,
    water_level_quantile_slices,
)
from rivercast.models.local_pipeline import (
    TrainRunResult,
    materialize_fixture_dataset,
    run_training,
)
from rivercast.models.package import load_model, predict, predictions_match, save_model
from rivercast.models.split import TemporalSplit, temporal_split
from rivercast.models.train import TrainResult, predict_candidate, train_candidate

__all__ = [
    "EvaluationReport",
    "PersistenceModel",
    "SliceMetric",
    "TemporalSplit",
    "TrainResult",
    "TrainRunResult",
    "evaluate_predictions",
    "load_model",
    "materialize_fixture_dataset",
    "predict",
    "predict_candidate",
    "predictions_match",
    "rising_falling_slices",
    "run_training",
    "save_model",
    "temporal_split",
    "train_candidate",
    "water_level_quantile_slices",
]
