"""Environment checks backing ``notebooks/00_environment_check.ipynb``.

Each check returns a :class:`CheckResult` with status:

- ``PASS`` — verified working;
- ``WARN`` — unavailable or not yet configured, acceptable at this phase
  (e.g. MLflow off-cluster, fixtures before Phase 2);
- ``FAIL`` — broken; the notebook's final cell raises on any FAIL.

The notebook only calls :func:`run_all`, :func:`summarize`, and
:func:`require_no_failures` — logic lives here (CLAUDE.md rule 17).
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rivercast.config import ConfigError, RivercastConfig, load_config
from rivercast.storage import LocalObjectStore, ObjectStoreError, create_object_store

Status = Literal["PASS", "WARN", "FAIL"]

MIN_PYTHON = (3, 11)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: str


def find_lab_root(start: Path | None = None) -> Path:
    """Walk upward until the rivercast lab root (its ``pyproject.toml``) is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        marker = candidate / "pyproject.toml"
        if marker.is_file() and 'name = "rivercast"' in marker.read_text(encoding="utf-8"):
            return candidate
    raise FileNotFoundError(
        f"could not find the rivercast lab root above {current}; "
        "run from inside labs/03_advanced/rivercast/"
    )


def check_python_version() -> CheckResult:
    version = sys.version_info[:3]
    detail = f"{platform.python_version()} on {platform.platform()}"
    if version < MIN_PYTHON:
        return CheckResult(
            "python_version",
            "FAIL",
            f"{detail} — need >= {'.'.join(map(str, MIN_PYTHON))}",
        )
    return CheckResult("python_version", "PASS", detail)


def check_package_import() -> CheckResult:
    try:
        module = importlib.import_module("rivercast")
    except ImportError as exc:
        return CheckResult(
            "package_import",
            "FAIL",
            f"cannot import rivercast ({exc}); run: python -m pip install -e '.[dev]'",
        )
    return CheckResult("package_import", "PASS", f"rivercast {module.__version__}")


def check_git_commit(lab_root: Path) -> CheckResult:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=lab_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult("git_commit", "WARN", f"git commit not determinable: {exc}")
    return CheckResult("git_commit", "PASS", f"HEAD = {commit}")


def check_config(config_path: Path) -> CheckResult:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        return CheckResult("config", "FAIL", str(exc))
    return CheckResult(
        "config",
        "PASS",
        f"{config_path.name}: mode={config.mode}, "
        f"stations={[s.name for s in config.stations]}, horizons={config.horizons_hours}",
    )


def check_writable_storage(config: RivercastConfig, lab_root: Path) -> CheckResult:
    """Round-trip a probe object through the configured store (local backend)."""
    if config.storage.backend != "local":
        return CheckResult(
            "writable_storage",
            "WARN",
            f"backend is {config.storage.backend!r}; write probe only implemented for 'local'",
        )
    root = Path(config.storage.root)
    if not root.is_absolute():
        root = lab_root / root
    try:
        store = LocalObjectStore(root)
        probe_key = f"envcheck/probe-{uuid.uuid4().hex}.txt"
        store.put_bytes(probe_key, b"rivercast environment check")
        payload = store.get_bytes(probe_key)
        if payload != b"rivercast environment check":
            return CheckResult("writable_storage", "FAIL", f"probe round-trip mismatch in {root}")
    except (OSError, ObjectStoreError) as exc:
        return CheckResult("writable_storage", "FAIL", f"cannot write to {root}: {exc}")
    return CheckResult("writable_storage", "PASS", f"probe object written under {root}")


def check_object_store_backend(config: RivercastConfig) -> CheckResult:
    try:
        create_object_store(config.storage)
    except ObjectStoreError as exc:
        return CheckResult("object_store_backend", "WARN", str(exc))
    return CheckResult("object_store_backend", "PASS", f"backend {config.storage.backend!r} ready")


def check_fixtures(lab_root: Path) -> CheckResult:
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    if not fixture_dir.is_dir():
        return CheckResult("fixtures", "WARN", f"{fixture_dir} missing (created in Phase 2)")
    files = [p for p in fixture_dir.rglob("*") if p.is_file() and p.suffix != ".md"]
    if not files:
        return CheckResult(
            "fixtures", "WARN", "fixture directory present but empty (Phase 2 fills it)"
        )
    return CheckResult("fixtures", "PASS", f"{len(files)} fixture file(s) in {fixture_dir.name}/")


def check_mlflow(config: RivercastConfig) -> CheckResult:
    try:
        version = importlib.metadata.version("mlflow")
    except importlib.metadata.PackageNotFoundError:
        return CheckResult("mlflow", "WARN", "mlflow not installed (needed from Phase 7)")
    uri = os.environ.get(config.mlflow.tracking_uri_env_var)
    if not uri:
        return CheckResult(
            "mlflow",
            "WARN",
            f"mlflow {version} installed; {config.mlflow.tracking_uri_env_var} not set "
            "(expected outside the workbench)",
        )
    return CheckResult("mlflow", "PASS", f"mlflow {version}; tracking URI configured")


def check_kfp() -> CheckResult:
    try:
        version = importlib.metadata.version("kfp")
    except importlib.metadata.PackageNotFoundError:
        return CheckResult("kfp", "WARN", "kfp SDK not installed (needed from Phase 8)")
    return CheckResult("kfp", "PASS", f"kfp {version}")


def check_cluster_api() -> CheckResult:
    token = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    if token.is_file():
        return CheckResult("cluster_api", "PASS", "in-cluster service-account token present")
    return CheckResult(
        "cluster_api",
        "WARN",
        "no in-cluster service-account token (expected outside an OpenShift workbench)",
    )


def run_all(config_path: Path | None = None, lab_root: Path | None = None) -> list[CheckResult]:
    root = lab_root or find_lab_root()
    cfg_path = config_path or root / "configs" / "local.yaml"
    results = [
        check_python_version(),
        check_package_import(),
        check_git_commit(root),
        check_config(cfg_path),
    ]
    try:
        config = load_config(cfg_path)
    except ConfigError:
        return results  # config FAIL already recorded; dependent checks impossible
    results += [
        check_writable_storage(config, root),
        check_object_store_backend(config),
        check_fixtures(root),
        check_mlflow(config),
        check_kfp(),
        check_cluster_api(),
    ]
    return results


def summarize(results: list[CheckResult]) -> str:
    width = max(len(r.name) for r in results)
    lines = [f"{r.status:<4}  {r.name:<{width}}  {r.detail}" for r in results]
    counts = {
        status: sum(1 for r in results if r.status == status) for status in ("PASS", "WARN", "FAIL")
    }
    lines.append(
        f"---   {counts['PASS']} passed, {counts['WARN']} warnings, {counts['FAIL']} failures"
    )
    return "\n".join(lines)


def require_no_failures(results: list[CheckResult]) -> None:
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        details = "; ".join(f"{r.name}: {r.detail}" for r in failures)
        raise RuntimeError(f"environment check failed — {details}")
