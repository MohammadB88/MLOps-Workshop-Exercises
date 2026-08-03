"""Tests for the release-metadata assembly script (PLAN.md Phase 13)."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.release_metadata import ReleaseMetadataError, build_release_metadata

_IMAGE_DIGESTS = {
    "data": "sha256:aaaa",
    "train": "sha256:bbbb",
    "ops": "sha256:cccc",
    "serving": "sha256:dddd",
}


def test_release_metadata_matches_plan_schema(lab_root: Path) -> None:
    metadata = build_release_metadata("v0.1.0-test", _IMAGE_DIGESTS, lab_root=lab_root)

    assert set(metadata) == {
        "git_commit",
        "release_version",
        "image_digests",
        "pipeline_spec_checksums",
        "schema_version",
        "feature_version",
        "compatible_workshop_version",
    }
    assert metadata["release_version"] == "v0.1.0-test"
    assert metadata["image_digests"] == _IMAGE_DIGESTS
    assert set(metadata["pipeline_spec_checksums"]) == {"rivercast-data-ops", "rivercast-model"}
    assert isinstance(metadata["git_commit"], str) and len(metadata["git_commit"]) == 40
    assert metadata["schema_version"] == 1
    assert metadata["feature_version"] == 1


def test_missing_image_digest_fails_closed(lab_root: Path) -> None:
    incomplete = {k: v for k, v in _IMAGE_DIGESTS.items() if k != "serving"}
    with pytest.raises(ReleaseMetadataError, match="serving"):
        build_release_metadata("v0.1.0-test", incomplete, lab_root=lab_root)


def test_missing_compiled_pipeline_fails_closed(tmp_path: Path, lab_root: Path) -> None:
    """A release must not report a checksum for a pipeline spec that was
    never (re)compiled -- rename one compiled YAML aside on the real lab
    tree (git commit resolution needs a real repo, so this can't run
    against an isolated copy) to prove this raises instead of silently
    omitting it, then restore it either way.
    """
    compiled = lab_root / "pipelines" / "compiled" / "rivercast-model.yaml"
    moved = tmp_path / "rivercast-model.yaml"
    compiled.rename(moved)
    try:
        with pytest.raises(ReleaseMetadataError, match="rivercast-model"):
            build_release_metadata("v0.1.0-test", _IMAGE_DIGESTS, lab_root=lab_root)
    finally:
        moved.rename(compiled)
