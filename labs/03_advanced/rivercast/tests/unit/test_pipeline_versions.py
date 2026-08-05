"""Compiled pipeline YAMLs carry a version tag matching their source
(PLAN.md Phase 15 "reproducibility: pipeline versions").

KFP has no native pipeline-version field at compile time; the version is
embedded as a ``[vN]`` prefix on the pipeline description instead, so it is
visible both in the source and in the compiled YAML's ``description:``
line without needing a separate side-channel file to keep in sync.
"""

from __future__ import annotations

from pathlib import Path

import yaml

LAB_ROOT = Path(__file__).resolve().parents[2]


def test_data_ops_pipeline_compiled_yaml_matches_source_version() -> None:
    from pipelines.data_ops_pipeline import PIPELINE_VERSION

    compiled = yaml.safe_load(
        (LAB_ROOT / "pipelines" / "compiled" / "rivercast-data-ops.yaml").read_text(
            encoding="utf-8"
        )
    )
    description = compiled["pipelineInfo"]["description"]
    assert description.startswith(f"[v{PIPELINE_VERSION}]")


def test_model_pipeline_compiled_yaml_matches_source_version() -> None:
    from pipelines.model_pipeline import PIPELINE_VERSION

    compiled = yaml.safe_load(
        (LAB_ROOT / "pipelines" / "compiled" / "rivercast-model.yaml").read_text(encoding="utf-8")
    )
    description = compiled["pipelineInfo"]["description"]
    assert description.startswith(f"[v{PIPELINE_VERSION}]")
