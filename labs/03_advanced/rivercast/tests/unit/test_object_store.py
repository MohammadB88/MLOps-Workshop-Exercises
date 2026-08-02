from pathlib import Path

import pytest

from rivercast.config import load_config
from rivercast.storage import (
    LocalObjectStore,
    ObjectExistsError,
    ObjectNotFoundError,
    ObjectStore,
    ObjectStoreError,
    create_object_store,
    zone_key,
)


@pytest.fixture()
def store(tmp_path: Path) -> LocalObjectStore:
    return LocalObjectStore(tmp_path / "artifacts")


def test_roundtrip(store: LocalObjectStore) -> None:
    store.put_bytes("bronze/a/b.json", b'{"v": 1}')
    assert store.get_bytes("bronze/a/b.json") == b'{"v": 1}'
    assert store.exists("bronze/a/b.json")
    assert not store.exists("bronze/a/missing.json")


def test_overwrite_is_refused_by_default(store: LocalObjectStore) -> None:
    store.put_bytes("bronze/x.json", b"first")
    with pytest.raises(ObjectExistsError, match="refusing to overwrite"):
        store.put_bytes("bronze/x.json", b"second")
    # Raw data unchanged (CLAUDE.md rule 9).
    assert store.get_bytes("bronze/x.json") == b"first"


def test_explicit_overwrite_is_allowed(store: LocalObjectStore) -> None:
    store.put_bytes("reports/latest.html", b"v1")
    store.put_bytes("reports/latest.html", b"v2", overwrite=True)
    assert store.get_bytes("reports/latest.html") == b"v2"


def test_get_missing_raises(store: LocalObjectStore) -> None:
    with pytest.raises(ObjectNotFoundError, match="nope.json"):
        store.get_bytes("silver/nope.json")


def test_list_keys_sorted_and_prefix_filtered(store: LocalObjectStore) -> None:
    for key in ("silver/b.parquet", "silver/a.parquet", "gold/c.parquet"):
        store.put_bytes(key, b"x")
    assert store.list_keys() == ["gold/c.parquet", "silver/a.parquet", "silver/b.parquet"]
    assert store.list_keys("silver/") == ["silver/a.parquet", "silver/b.parquet"]


@pytest.mark.parametrize(
    "bad_key",
    ["", "  padded  ", "/absolute.json", "back\\slash.json", "a/../escape.json", "a//b.json"],
)
def test_invalid_keys_rejected(store: LocalObjectStore, bad_key: str) -> None:
    with pytest.raises(ObjectStoreError, match="invalid object key"):
        store.put_bytes(bad_key, b"x")


def test_factory_builds_local_store(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # local.yaml root is relative: ./artifacts
    config = load_config(configs_dir / "local.yaml")
    built = create_object_store(config.storage)
    assert isinstance(built, ObjectStore)


def test_factory_rejects_unimplemented_s3(configs_dir: Path) -> None:
    config = load_config(configs_dir / "openshift.yaml")
    with pytest.raises(ObjectStoreError, match="not implemented yet"):
        create_object_store(config.storage)


def test_zone_key_builds_and_validates(configs_dir: Path) -> None:
    config = load_config(configs_dir / "local.yaml")
    zones = config.storage.zones
    assert zone_key(zones, "bronze", "source=pegelonline", "x.json") == (
        "bronze/source=pegelonline/x.json"
    )
    with pytest.raises(ObjectStoreError, match="unknown storage zone"):
        zone_key(zones, "platinum", "x.json")
    with pytest.raises(ObjectStoreError, match="at least one path part"):
        zone_key(zones, "gold")
