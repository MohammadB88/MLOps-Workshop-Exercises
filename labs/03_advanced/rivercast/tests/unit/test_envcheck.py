from pathlib import Path

import pytest

from rivercast.envcheck import (
    CheckResult,
    check_config,
    check_package_import,
    check_python_version,
    find_lab_root,
    require_no_failures,
    run_all,
    summarize,
)


def test_find_lab_root_from_tests_dir(lab_root: Path) -> None:
    assert find_lab_root(Path(__file__).parent) == lab_root


def test_find_lab_root_outside_project_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="lab root"):
        find_lab_root(tmp_path)


def test_core_checks_pass_here(configs_dir: Path) -> None:
    assert check_python_version().status == "PASS"
    assert check_package_import().status == "PASS"
    assert check_config(configs_dir / "local.yaml").status == "PASS"


def test_invalid_config_yields_fail_not_exception(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("mode: nope\n", encoding="utf-8")
    result = check_config(bad)
    assert result.status == "FAIL"
    assert "mode" in result.detail


def test_run_all_has_no_failures_in_dev_environment(lab_root: Path) -> None:
    results = run_all(lab_root=lab_root)
    failures = [r for r in results if r.status == "FAIL"]
    assert failures == []
    require_no_failures(results)  # must not raise


def test_require_no_failures_raises_with_details() -> None:
    results = [CheckResult("thing", "FAIL", "it broke")]
    with pytest.raises(RuntimeError, match="thing: it broke"):
        require_no_failures(results)


def test_summarize_mentions_every_check() -> None:
    results = [
        CheckResult("alpha", "PASS", "ok"),
        CheckResult("beta", "WARN", "later"),
    ]
    text = summarize(results)
    assert "alpha" in text and "beta" in text
    assert "1 passed, 1 warnings, 0 failures" in text
