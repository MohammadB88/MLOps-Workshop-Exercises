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


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "config" and args.config_command == "validate":
        return _cmd_config_validate(args.config)
    if args.command == "envcheck":
        return _cmd_envcheck(args.config)
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
