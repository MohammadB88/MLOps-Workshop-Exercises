"""Object storage with a single interface for local filesystem and (later) S3.

Keys are S3-style: forward-slash separated, relative, no ``..`` segments. The
local backend is the development and fixture-mode implementation; the S3
backend arrives with the pipeline phases and must honor the same contract.

Writes never overwrite by default — raw data is immutable (CLAUDE.md rule 9);
callers must opt in explicitly for the few artifacts that are replaceable.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rivercast.config import StorageConfig


class ObjectStoreError(Exception):
    """Base error for object-store operations."""


class ObjectExistsError(ObjectStoreError):
    """Write refused because the key already exists and overwrite was not set."""


class ObjectNotFoundError(ObjectStoreError):
    """Read failed because the key does not exist."""


@runtime_checkable
class ObjectStore(Protocol):
    def put_bytes(self, key: str, data: bytes, *, overwrite: bool = False) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def list_keys(self, prefix: str = "") -> list[str]: ...


def _validate_key(key: str) -> str:
    if not key or key != key.strip():
        raise ObjectStoreError(f"invalid object key: {key!r} (empty or surrounding whitespace)")
    if "\\" in key:
        raise ObjectStoreError(f"invalid object key: {key!r} (use '/' separators, not '\\')")
    if key.startswith("/"):
        raise ObjectStoreError(f"invalid object key: {key!r} (keys are relative, no leading '/')")
    parts = key.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ObjectStoreError(f"invalid object key: {key!r} (empty, '.' or '..' path segment)")
    return key


class LocalObjectStore:
    """Filesystem-backed store; one file per key below ``root``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root.joinpath(*_validate_key(key).split("/"))

    def put_bytes(self, key: str, data: bytes, *, overwrite: bool = False) -> None:
        target = self._path(key)
        if target.exists() and not overwrite:
            raise ObjectExistsError(
                f"refusing to overwrite existing object {key!r}; "
                "pass overwrite=True only for replaceable artifacts"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file in the same directory, then atomically replace,
        # so readers never observe partial objects.
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".partial")
        try:
            with os.fdopen(fd, "wb") as tmp_file:
                tmp_file.write(data)
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def get_bytes(self, key: str) -> bytes:
        target = self._path(key)
        if not target.is_file():
            raise ObjectNotFoundError(f"object not found: {key!r} (under {self.root})")
        return target.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list_keys(self, prefix: str = "") -> list[str]:
        if prefix:
            # A prefix may end with "/" (S3 semantics); validate the rest.
            trimmed = prefix.rstrip("/")
            if not trimmed:
                raise ObjectStoreError(f"invalid key prefix: {prefix!r}")
            _validate_key(trimmed)
        keys = [
            p.relative_to(self.root).as_posix()
            for p in self.root.rglob("*")
            if p.is_file() and not p.name.startswith(".tmp-")
        ]
        return sorted(k for k in keys if k.startswith(prefix))


def create_object_store(storage: StorageConfig) -> ObjectStore:
    """Build the configured store. S3 arrives with the pipeline phases."""
    if storage.backend == "local":
        return LocalObjectStore(storage.root)
    raise ObjectStoreError(
        "storage.backend 's3' is configured but the S3 backend is not implemented yet "
        "(planned for the pipeline phases); use backend 'local' for now"
    )
