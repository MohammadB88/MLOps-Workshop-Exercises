"""Shared plumbing for RiverCast pipeline components (PLAN.md Phase 8).

Every component under ``components/`` follows the same shape:

- a pure ``run(...)`` function, callable directly from a notebook or a test,
  accepting explicit typed parameters (object-store keys/paths, config
  values) and returning a :class:`ComponentResult`;
- a thin ``main()`` CLI wrapper (argparse) that calls ``run()``, prints the
  result as one JSON object on stdout, and exits non-zero on any contract
  failure (rule 13: fail closed) so a KFP step fails the DAG instead of
  silently continuing.

Components read and write large data through :class:`~rivercast.storage.ObjectStore`
keys, not KFP scalar outputs (plan §Phase 8 component contract); ``main()``
only ever prints the small JSON result, never a full dataset.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from mlflow.exceptions import MlflowException

from rivercast.config import RivercastConfig, load_config
from rivercast.gitinfo import current_commit
from rivercast.log import get_logger
from rivercast.storage import ObjectStore, create_object_store


class ComponentError(Exception):
    """Raised for a contract failure; ``main()`` turns this into exit code 1."""


@dataclass(frozen=True)
class ComponentResult:
    """The small JSON envelope every component emits (plan §Phase 8).

    ``output_keys`` lists the object-store keys this run wrote (the actual
    data), so the caller/pipeline can pass them to the next step without any
    large payload crossing the component boundary itself.
    """

    component: str
    status: str  # "ok" | "failed"
    output_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    code_commit: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True, default=str)


def load_component_config(config_path: Path) -> RivercastConfig:
    return load_config(config_path)


def open_store(config: RivercastConfig, lab_root: Path) -> ObjectStore:
    """Resolve the configured object store, anchoring a relative local root
    under ``lab_root`` the same way ``envcheck.check_writable_storage`` does.
    """
    if config.storage.backend == "local":
        root = Path(config.storage.root)
        if not root.is_absolute():
            root = lab_root / root
        resolved = config.storage.model_copy(update={"root": str(root)})
        return create_object_store(resolved)
    return create_object_store(config.storage)


def read_json(store: ObjectStore, key: str) -> Any:
    return json.loads(store.get_bytes(key).decode("utf-8"))


def write_json(store: ObjectStore, key: str, payload: Any, *, overwrite: bool = False) -> None:
    store.put_bytes(
        key,
        json.dumps(payload, indent=1, sort_keys=True, default=str).encode("utf-8"),
        overwrite=overwrite,
    )


def emit(result: ComponentResult) -> None:
    """Print the result JSON to stdout and exit non-zero if it failed."""
    print(result.to_json())
    if result.status != "ok":
        sys.exit(1)


def component_logger(name: str) -> Any:
    return get_logger(f"components.{name}")


def with_git_commit(lab_root: Path) -> str | None:
    return current_commit(lab_root)


def model_run_uri(client: Any, registered_model_name: str, model_version: str) -> str:
    """``runs:/<run_id>/model`` for a registered model version, instead of
    ``models:/<name>/<version>``.

    Workaround for a real upstream bug: as of mlflow 3.15, loading via
    ``models:/...`` on Windows raises
    ``MlflowException: Could not find a registered artifact repository for: c:``
    because ``mlflow.models.model.Model.load()`` re-passes an already-resolved
    native Windows path (``C:\\...\\MLmodel``) through ``urllib.parse.urlparse``,
    which misreads the drive letter as a URI scheme. Loading the same
    artifact via ``runs:/<run_id>/model`` does not hit that code path and
    works correctly cross-platform; every component that loads a registered
    model (``deploy``, ``forecast``) goes through this helper instead of
    building a ``models:/`` URI directly.
    """
    model_version_obj = client.get_model_version(registered_model_name, model_version)
    return f"runs:/{model_version_obj.run_id}/model"


def champion_run_uri(client: Any, registered_model_name: str) -> str | None:
    """``runs:/<run_id>/model`` for the current ``champion`` alias, or
    ``None`` if no champion is set yet. See :func:`model_run_uri`.
    """
    try:
        champion = client.get_model_version_by_alias(registered_model_name, "champion")
    except MlflowException:
        return None
    return f"runs:/{champion.run_id}/model"
