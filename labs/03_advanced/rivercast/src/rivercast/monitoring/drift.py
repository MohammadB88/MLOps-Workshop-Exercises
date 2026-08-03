"""Feature and prediction drift reports via Evidently (PLAN.md Phase 12).

Drift is a signal to investigate, never a retraining trigger by itself
(ADR 0003, plan §Phase 12: "Do not retrain solely because feature drift is
detected"). This module only classifies and reports; the retraining
decision lives entirely in :mod:`rivercast.monitoring.performance`.

Built against Evidently 0.7's current top-level API
(``evidently.Report``/``evidently.presets``), not the legacy
``evidently.report.Report``/``evidently.metric_preset`` surface the PLAN.md
reference links describe -- that module was removed in the 0.7 rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

_DRIFTED_COLUMNS_METRIC_PREFIX = "DriftedColumnsCount"


@dataclass(frozen=True)
class DriftReport:
    checked_at_utc: str
    reference_row_count: int
    current_row_count: int
    columns_checked: list[str]
    drifted_share: float
    is_warning: bool
    snapshot_json: str


def run_drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str],
    *,
    warning_threshold: float,
    now_utc: datetime | None = None,
) -> DriftReport:
    """Compare ``current`` against a ``reference`` window over ``columns``.

    Fails closed on empty input (rule 13): an empty reference or current
    frame cannot produce a meaningful drift comparison, so this raises
    rather than silently reporting "no drift".
    """
    if reference.empty:
        raise ValueError("reference window is empty; cannot compute drift")
    if current.empty:
        raise ValueError("current window is empty; cannot compute drift")
    missing = [c for c in columns if c not in reference.columns or c not in current.columns]
    if missing:
        raise ValueError(f"columns missing from reference or current frame: {missing}")

    now = now_utc or datetime.now(UTC)
    report = Report(metrics=[DataDriftPreset()])
    snapshot = report.run(current_data=current[columns], reference_data=reference[columns])
    snapshot_dict = snapshot.dict()

    drifted_share = 0.0
    for metric in snapshot_dict["metrics"]:
        if metric["metric_name"].startswith(_DRIFTED_COLUMNS_METRIC_PREFIX):
            drifted_share = float(metric["value"]["share"])
            break

    return DriftReport(
        checked_at_utc=now.isoformat(timespec="seconds"),
        reference_row_count=len(reference),
        current_row_count=len(current),
        columns_checked=columns,
        drifted_share=drifted_share,
        is_warning=drifted_share > warning_threshold,
        snapshot_json=snapshot.json(),
    )
