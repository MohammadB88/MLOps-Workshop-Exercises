"""``rivercast`` command-line interface.

Phase 1 exposes configuration validation and environment checks; later phases
add their commands here (``rivercast train ...`` etc.).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import rivercast
from rivercast.config import ConfigError, load_config
from rivercast.envcheck import find_lab_root, require_no_failures, run_all, summarize
from rivercast.models.local_pipeline import report_to_json, run_training
from rivercast.models.mlflow_pipeline import train_track_and_register


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rivercast",
        description=(
            "RiverCast — Level-1 continuous forecasting capstone lab. "
            "Educational system; not a flood-warning product."
        ),
    )
    parser.add_argument("--version", action="version", version=f"rivercast {rivercast.__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    config_cmd = subcommands.add_parser("config", help="configuration operations")
    config_sub = config_cmd.add_subparsers(dest="config_command", required=True)
    validate = config_sub.add_parser("validate", help="load and validate a configuration file")
    validate.add_argument(
        "--config",
        required=True,
        type=Path,
        help="path to the configuration file (e.g. configs/local.yaml)",
    )

    envcheck_cmd = subcommands.add_parser(
        "envcheck", help="run the environment checks used by 00_environment_check.ipynb"
    )
    envcheck_cmd.add_argument(
        "--config",
        type=Path,
        default=None,
        help="configuration file (default: <lab root>/configs/local.yaml)",
    )

    train_cmd = subcommands.add_parser(
        "train", help="train a candidate against persistence in fixture mode (Phase 6)"
    )
    train_cmd.add_argument(
        "--config", type=Path, default=None, help="configuration file (default: configs/local.yaml)"
    )
    train_cmd.add_argument(
        "--horizon", type=int, required=True, help="forecast horizon in hours, e.g. 6 or 12"
    )
    train_cmd.add_argument(
        "--model",
        choices=["ridge", "hist-gradient-boosting"],
        required=True,
        help="candidate model family",
    )
    train_cmd.add_argument("--seed", type=int, default=42, help="random seed (default: 42)")
    train_cmd.add_argument(
        "--dataset-id",
        default=None,
        help=(
            "reserved for the object-store-backed dataset in later phases; "
            "Phase 6 always materializes from the committed fixtures and ignores this value"
        ),
    )
    train_cmd.add_argument(
        "--track-mlflow",
        action="store_true",
        help="log the run to MLflow and register it as a candidate model version (Phase 7)",
    )
    train_cmd.add_argument(
        "--promote",
        action="store_true",
        help=(
            "if the promotion gates pass, run the promotion transaction and move the "
            "champion alias; implies --track-mlflow; no-op deploy/smoke-test stub until "
            "Phases 8-11 add real serving"
        ),
    )
    return parser


def _cmd_config_validate(config_path: Path) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(
        f"OK: {config_path} is a valid RiverCast configuration "
        f"(mode={config.mode}, stations={[s.name for s in config.stations]}, "
        f"horizons={config.horizons_hours}, storage={config.storage.backend})"
    )
    return 0


def _cmd_envcheck(config_path: Path | None) -> int:
    results = run_all(config_path=config_path, lab_root=find_lab_root())
    print(summarize(results))
    try:
        require_no_failures(results)
    except RuntimeError:
        return 1
    return 0


def _cmd_train(
    config_path: Path | None, horizon: int, model: str, seed: int, track_mlflow: bool, promote: bool
) -> int:
    lab_root = find_lab_root()
    resolved_config_path = config_path or lab_root / "configs" / "local.yaml"
    try:
        config = load_config(resolved_config_path)
    except ConfigError as exc:
        print(f"INVALID CONFIG: {exc}", file=sys.stderr)
        return 2

    if track_mlflow or promote:
        try:
            outcome = train_track_and_register(
                config=config,
                lab_root=lab_root,
                fixture_dir=lab_root / "data_fixtures" / "pegelonline",
                horizon_hours=horizon,
                model_name=model,  # type: ignore[arg-type]
                models_dir=lab_root / "models" / "local",
                seed=seed,
                promote=promote,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"TRAINING FAILED: {exc}", file=sys.stderr)
            return 1

        print(report_to_json(outcome.train_result))
        print(
            f"\nmlflow run: {outcome.logged_run.run_id}"
            f"\nregistered: {outcome.registered_model_name} v{outcome.model_version.version}"
            f"\npromotion gates: {'PASS' if outcome.decision.approved else 'REJECTED'}"
            + ("" if outcome.decision.approved else f" ({'; '.join(outcome.decision.reasons)})")
            + f"\npromoted to champion: {outcome.promoted}"
        )
        return 0

    try:
        result = run_training(
            config=config,
            fixture_dir=lab_root / "data_fixtures" / "pegelonline",
            horizon_hours=horizon,
            model_name=model,  # type: ignore[arg-type]
            models_dir=lab_root / "models" / "local",
            seed=seed,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"TRAINING FAILED: {exc}", file=sys.stderr)
        return 1

    print(report_to_json(result))
    print(
        f"\nmodel saved to {result.model_path}\n"
        f"test skill vs. persistence: {result.test_report.skill_vs_persistence:.3f}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "config" and args.config_command == "validate":
        return _cmd_config_validate(args.config)
    if args.command == "envcheck":
        return _cmd_envcheck(args.config)
    if args.command == "train":
        return _cmd_train(
            args.config, args.horizon, args.model, args.seed, args.track_mlflow, args.promote
        )
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
