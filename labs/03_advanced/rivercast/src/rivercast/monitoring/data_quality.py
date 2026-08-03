"""Data-monitoring report: freshness/coverage/missingness (Phase 4/8's
``rivercast.processing.quality``) plus an Evidently data-summary snapshot
(PLAN.md Phase 12).

Works with or without labels: a :class:`DataQualityMonitoringReport` only
needs the hourly canonical window itself, so it is produced identically
whether or not any prediction has matured yet -- the plan's "Reports work
with no labels and with delayed labels" acceptance criterion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from evidently import Report
from evidently.presets import DataSummaryPreset

from rivercast.contracts.hourly import HourlyObservation
from rivercast.processing.quality import QualityReport


@dataclass(frozen=True)
class DataQualityMonitoringReport:
    checked_at_utc: str
    row_count: int
    station_count: int
    missing_row_count: int
    quality_report: QualityReport
    evidently_snapshot_json: str


def _hourly_to_frame(hourly: list[HourlyObservation]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "station_uuid": [o.station_uuid for o in hourly],
            "value": [o.value for o in hourly],
            "is_missing": [o.is_missing for o in hourly],
            "source_lag_minutes": [o.source_lag_minutes for o in hourly],
        }
    )


def run_data_quality_report(
    hourly: list[HourlyObservation],
    quality_report: QualityReport,
    *,
    now_utc: datetime | None = None,
) -> DataQualityMonitoringReport:
    """Summarize one hourly window: existing fail-closed checks plus an
    Evidently data-summary snapshot for the richer HTML view.

    Fails closed on an empty window (rule 13) rather than reporting a
    meaningless empty summary.
    """
    if not hourly:
        raise ValueError("hourly window is empty; cannot produce a data-quality report")

    now = now_utc or datetime.now(UTC)
    frame = _hourly_to_frame(hourly)

    report = Report(metrics=[DataSummaryPreset()])
    snapshot = report.run(current_data=frame)

    return DataQualityMonitoringReport(
        checked_at_utc=now.isoformat(timespec="seconds"),
        row_count=len(hourly),
        station_count=len({o.station_uuid for o in hourly}),
        missing_row_count=sum(1 for o in hourly if o.is_missing),
        quality_report=quality_report,
        evidently_snapshot_json=snapshot.json(),
    )
