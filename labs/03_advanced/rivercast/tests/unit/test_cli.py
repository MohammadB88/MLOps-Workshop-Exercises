from pathlib import Path

import pytest

from rivercast.cli import main


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert "rivercast" in capsys.readouterr().out


def test_config_validate_success(configs_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["config", "validate", "--config", str(configs_dir / "local.yaml")])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert out.startswith("OK:")
    assert "KAUB" in out


def test_config_validate_invalid_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("mode: production\n", encoding="utf-8")
    exit_code = main(["config", "validate", "--config", str(bad)])
    assert exit_code == 2
    err = capsys.readouterr().err
    assert err.startswith("INVALID:")
    assert "mode" in err


def test_config_validate_missing_file_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["config", "validate", "--config", str(tmp_path / "nope.yaml")])
    assert exit_code == 2
    assert "not found" in capsys.readouterr().err
