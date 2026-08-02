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
from rivercast.models.mlflow_pipeline import TrackedTrainingOutcome, train_track_and_register
from rivercast.models.package import load_model, predict, predictions_match, save_model
from rivercast.models.registry import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    PromotionDecision,
    assign_challenger,
    champion_test_report,
    evaluate_promotion_gates,
    get_champion,
    promote_challenger_to_champion,
    register_candidate,
    reject_candidate,
)
from rivercast.models.split import TemporalSplit, temporal_split
from rivercast.models.tracking import LoggedRun, log_training_run, resolve_tracking_uri
from rivercast.models.train import TrainResult, predict_candidate, train_candidate

__all__ = [
    "CHALLENGER_ALIAS",
    "CHAMPION_ALIAS",
    "EvaluationReport",
    "LoggedRun",
    "PersistenceModel",
    "PromotionDecision",
    "SliceMetric",
    "TemporalSplit",
    "TrackedTrainingOutcome",
    "TrainResult",
    "TrainRunResult",
    "assign_challenger",
    "champion_test_report",
    "evaluate_predictions",
    "evaluate_promotion_gates",
    "get_champion",
    "load_model",
    "log_training_run",
    "materialize_fixture_dataset",
    "predict",
    "predict_candidate",
    "predictions_match",
    "promote_challenger_to_champion",
    "register_candidate",
    "reject_candidate",
    "resolve_tracking_uri",
    "rising_falling_slices",
    "run_training",
    "save_model",
    "temporal_split",
    "train_candidate",
    "train_track_and_register",
    "water_level_quantile_slices",
]
