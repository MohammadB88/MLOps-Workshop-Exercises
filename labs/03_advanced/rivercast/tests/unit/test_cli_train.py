"""CLI tests for `rivercast train` (offline, fixture-mode)."""

import json

import pytest

from rivercast.cli import main


def test_train_ridge_horizon_6_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["train", "--horizon", "6", "--model", "ridge"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "model saved to" in out
    payload = json.loads(out.split("\n\nmodel saved to")[0])
    assert payload["horizon_hours"] == 6
    assert payload["model_name"] == "ridge"
    assert "skill_vs_persistence" in payload["test"]


def test_train_rejects_bad_horizon(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["train", "--horizon", "99", "--model", "ridge"])
    assert exit_code == 1
    assert "TRAINING FAILED" in capsys.readouterr().err


def test_train_rejects_unknown_model() -> None:
    with pytest.raises(SystemExit):
        main(["train", "--horizon", "6", "--model", "random-forest"])


def test_train_dataset_id_flag_accepted_but_documented_as_ignored(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["train", "--horizon", "6", "--model", "ridge", "--dataset-id", "sha256:doesnotexist"]
    )
    assert exit_code == 0  # Phase 6 always materializes from fixtures; flag is a no-op for now
