"""Assemble release metadata for a RiverCast release (PLAN.md Phase 13).

Run from CI after images are built and pipelines are compiled:

    python -m scripts.release_metadata \\
        --release-version v0.1.0 \\
        --image-digest data=sha256:... --image-digest train=sha256:... \\
        --image-digest ops=sha256:... --image-digest serving=sha256:... \\
        --output release_metadata.json

Prints the plan's exact schema (git_commit, release_version, image_digests,
pipeline_spec_checksums, schema_version, feature_version,
compatible_workshop_version) as one JSON object. Fails closed: a missing
digest for a configured image, an uncompiled pipeline, or an unreadable
config all raise rather than emitting partial/placeholder metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rivercast.config import load_config
from rivercast.gitinfo import current_commit

_LAB_ROOT = Path(__file__).resolve().parents[1]
_REQUIRED_IMAGES = ("data", "train", "ops", "serving")
_PIPELINE_SPECS = (
    "pipelines/compiled/rivercast-data-ops.yaml",
    "pipelines/compiled/rivercast-model.yaml",
)


class ReleaseMetadataError(Exception):
    """Raised when release metadata cannot be assembled completely (fail closed)."""


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ReleaseMetadataError(
            f"compiled pipeline spec not found: {path} (run `python -m pipelines.<name>` first)"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_release_metadata(
    release_version: str,
    image_digests: dict[str, str],
    lab_root: Path = _LAB_ROOT,
    config_path: Path | None = None,
) -> dict[str, object]:
    missing_images = sorted(set(_REQUIRED_IMAGES) - set(image_digests))
    if missing_images:
        raise ReleaseMetadataError(f"missing image digest(s) for: {missing_images}")

    commit = current_commit(lab_root)
    if commit is None:
        raise ReleaseMetadataError("could not resolve the current Git commit")

    config = load_config(config_path or lab_root / "configs" / "base.yaml")

    pipeline_spec_checksums = {
        Path(spec).stem: _sha256_file(lab_root / spec) for spec in _PIPELINE_SPECS
    }

    return {
        "git_commit": commit,
        "release_version": release_version,
        "image_digests": {name: image_digests[name] for name in _REQUIRED_IMAGES},
        "pipeline_spec_checksums": pipeline_spec_checksums,
        "schema_version": config.schema_version,
        "feature_version": config.feature_version,
        "compatible_workshop_version": release_version,
    }


def _parse_image_digest(value: str) -> tuple[str, str]:
    name, _, digest = value.partition("=")
    if not name or not digest:
        raise argparse.ArgumentTypeError(f"expected NAME=DIGEST, got {value!r}")
    return name, digest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assemble RiverCast release metadata")
    parser.add_argument("--release-version", required=True)
    parser.add_argument(
        "--image-digest",
        action="append",
        type=_parse_image_digest,
        default=[],
        metavar="NAME=DIGEST",
        help=f"repeatable; one of {_REQUIRED_IMAGES}",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="write JSON here instead of stdout"
    )
    args = parser.parse_args(argv)

    metadata = build_release_metadata(args.release_version, dict(args.image_digest))
    payload = json.dumps(metadata, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
