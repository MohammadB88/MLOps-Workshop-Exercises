"""Duplicate-run protection for scheduled pipelines (PLAN.md Phase 15).

A recurring KFP run and a manually-triggered run of the same pipeline can
overlap (a slow run still executing when the next scheduled tick fires, or an
operator re-triggering by hand). Both pipelines write through the same
object-store keys and the same MLflow registry aliases, so two concurrent
executions racing on those writes -- not two executions existing -- is the
actual hazard; ``RawArchive``/``trigger`` idempotency (Phases 3, 10) already
make a *sequential* rerun safe and cheap. This module adds the missing piece:
refuse to start a second run while one is still in flight.

The lock is a plain marker object in the object store, keyed by pipeline
name, holding the owning run's id and start time. It is advisory (nothing
stops a caller from bypassing :class:`PipelineRunLock`), which is
sufficient here: every entrypoint that can start one of these pipelines
(CLI, KFP recurring run) goes through this module rather than writing the
marker itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from rivercast.storage.object_store import ObjectExistsError, ObjectNotFoundError, ObjectStore


class PipelineAlreadyRunningError(Exception):
    """Raised when a lock is requested while another run still holds it."""


def _lock_key(pipeline_name: str) -> str:
    return f"locks/{pipeline_name}.lock.json"


@dataclass(frozen=True)
class LockInfo:
    pipeline_name: str
    run_id: str
    acquired_at_utc: str
    released: bool = False

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "pipeline_name": self.pipeline_name,
                "run_id": self.run_id,
                "acquired_at_utc": self.acquired_at_utc,
                "released": self.released,
            },
            sort_keys=True,
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> LockInfo:
        payload = json.loads(data.decode("utf-8"))
        return cls(**payload)


class PipelineRunLock:
    """Advisory, object-store-backed mutex for one named pipeline.

    A lock older than ``stale_after_seconds`` is treated as abandoned (a
    crashed run that never released it) and is safe to reclaim -- otherwise
    one hard-killed run would permanently wedge every future scheduled tick,
    which is a worse failure mode than the rare double-run this guard exists
    to prevent.
    """

    def __init__(self, store: ObjectStore, *, stale_after_seconds: float = 6 * 3600) -> None:
        self._store = store
        self._stale_after_seconds = stale_after_seconds

    def _read(self, pipeline_name: str) -> LockInfo | None:
        try:
            return LockInfo.from_bytes(self._store.get_bytes(_lock_key(pipeline_name)))
        except ObjectNotFoundError:
            return None

    def is_locked(self, pipeline_name: str, *, now: datetime | None = None) -> bool:
        existing = self._read(pipeline_name)
        if existing is None or existing.released:
            return False
        return not self._is_stale(existing, now=now)

    def _is_stale(self, lock: LockInfo, *, now: datetime | None = None) -> bool:
        now = now if now is not None else datetime.now(UTC)
        acquired = datetime.fromisoformat(lock.acquired_at_utc)
        age_seconds = (now - acquired).total_seconds()
        return age_seconds > self._stale_after_seconds

    def acquire(self, pipeline_name: str, run_id: str, *, now: datetime | None = None) -> LockInfo:
        """Take the lock, or raise if another run genuinely still holds it.

        Fails closed on ambiguity: a lock that cannot be read as valid JSON
        counts as held (never silently overwritten), matching rule 13.
        """
        now = now if now is not None else datetime.now(UTC)
        existing = self._read(pipeline_name)
        if existing is not None and not existing.released and not self._is_stale(existing, now=now):
            raise PipelineAlreadyRunningError(
                f"pipeline {pipeline_name!r} is already running "
                f"(run_id={existing.run_id!r}, acquired_at={existing.acquired_at_utc})"
            )
        info = LockInfo(
            pipeline_name=pipeline_name,
            run_id=run_id,
            acquired_at_utc=now.isoformat(timespec="seconds"),
        )
        key = _lock_key(pipeline_name)
        try:
            self._store.put_bytes(key, info.to_bytes(), overwrite=False)
        except ObjectExistsError:
            # A stale/released lock still needs an explicit overwrite; a
            # fresh one that appeared between _read and put_bytes is a real
            # race, which reclaiming here would incorrectly steal -- re-check.
            existing = self._read(pipeline_name)
            if (
                existing is not None
                and not existing.released
                and not self._is_stale(existing, now=now)
            ):
                raise PipelineAlreadyRunningError(
                    f"pipeline {pipeline_name!r} is already running "
                    f"(run_id={existing.run_id!r}, acquired_at={existing.acquired_at_utc})"
                ) from None
            self._store.put_bytes(key, info.to_bytes(), overwrite=True)
        return info

    def release(self, pipeline_name: str, run_id: str) -> None:
        """Release the lock, but only if we still own it.

        Silently no-ops if the lock was already released or reclaimed by a
        stale-lock takeover -- a release racing a legitimate new owner must
        never delete that new owner's lock.
        """
        existing = self._read(pipeline_name)
        if existing is None or existing.run_id != run_id or existing.released:
            return
        # Overwrite with a released marker rather than attempting a delete --
        # ObjectStore has no delete primitive (writes are append/overwrite
        # only, matching the immutability contract this store is built on).
        released = LockInfo(
            pipeline_name=existing.pipeline_name,
            run_id=existing.run_id,
            acquired_at_utc=existing.acquired_at_utc,
            released=True,
        )
        self._store.put_bytes(_lock_key(pipeline_name), released.to_bytes(), overwrite=True)
