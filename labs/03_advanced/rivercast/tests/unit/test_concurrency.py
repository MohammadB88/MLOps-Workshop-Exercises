"""Duplicate-run lock tests (PLAN.md Phase 15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rivercast.concurrency import PipelineAlreadyRunningError, PipelineRunLock
from rivercast.storage import LocalObjectStore


@pytest.fixture()
def store(tmp_path: Path) -> LocalObjectStore:
    return LocalObjectStore(tmp_path / "artifacts")


def test_acquire_when_unlocked_succeeds(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store)
    assert not lock.is_locked("rivercast-data-ops")
    info = lock.acquire("rivercast-data-ops", "run-1")
    assert info.run_id == "run-1"
    assert lock.is_locked("rivercast-data-ops")


def test_second_acquire_while_held_is_refused(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store)
    lock.acquire("rivercast-data-ops", "run-1")
    with pytest.raises(PipelineAlreadyRunningError, match="run-1"):
        lock.acquire("rivercast-data-ops", "run-2")


def test_release_then_acquire_by_a_new_run_succeeds(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store)
    lock.acquire("rivercast-data-ops", "run-1")
    lock.release("rivercast-data-ops", "run-1")
    assert not lock.is_locked("rivercast-data-ops")
    info = lock.acquire("rivercast-data-ops", "run-2")
    assert info.run_id == "run-2"


def test_release_by_a_non_owner_is_a_no_op(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store)
    lock.acquire("rivercast-data-ops", "run-1")
    lock.release("rivercast-data-ops", "some-other-run")
    assert lock.is_locked("rivercast-data-ops")


def test_stale_lock_is_reclaimable(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store, stale_after_seconds=60)
    long_ago = datetime.now(UTC) - timedelta(hours=6)
    lock.acquire("rivercast-data-ops", "crashed-run", now=long_ago)
    assert not lock.is_locked("rivercast-data-ops")
    info = lock.acquire("rivercast-data-ops", "new-run")
    assert info.run_id == "new-run"


def test_fresh_lock_is_not_stale(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store, stale_after_seconds=3600)
    lock.acquire("rivercast-data-ops", "run-1")
    assert lock.is_locked("rivercast-data-ops")
    with pytest.raises(PipelineAlreadyRunningError):
        lock.acquire("rivercast-data-ops", "run-2")


def test_locks_are_scoped_per_pipeline_name(store: LocalObjectStore) -> None:
    lock = PipelineRunLock(store)
    lock.acquire("rivercast-data-ops", "run-1")
    # A different pipeline name is unaffected -- the model pipeline can run
    # concurrently with the data-ops pipeline.
    info = lock.acquire("rivercast-model", "run-2")
    assert info.run_id == "run-2"
