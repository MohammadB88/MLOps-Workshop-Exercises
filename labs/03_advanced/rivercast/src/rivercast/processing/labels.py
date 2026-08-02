"""Label construction: future target-station levels at fixed horizons (Phase 5).

``target_level_{h}h`` for issue time ``t`` is the target station's value at
``t + h``, matched with an explicit tolerance (rule: use only information
available at forecast issue time for *features*; labels are deliberately the
one place the pipeline looks forward, and only to the single future value
being predicted). Rows whose label falls outside the matched hourly grid (or
whose match is missing/stale) get ``NaN`` — excluded from training but kept
for live forecasting, per the Phase 5 acceptance criteria.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from rivercast.contracts.hourly import HourlyObservation


def build_labels(
    hourly: list[HourlyObservation],
    target_station_uuid: str,
    issue_times: pd.DatetimeIndex,
    horizons_hours: list[int],
    match_tolerance_minutes: float,
) -> pd.DataFrame:
    """One label column per horizon, indexed by issue time.

    A label is populated only when a target-station hourly value exists at
    exactly ``issue_time + horizon`` on the canonical grid — the grid is
    already hourly, so "tolerance" here means: the target hour must be
    present and not itself ``is_missing``. ``match_tolerance_minutes`` is
    accepted for interface symmetry with the config threshold and to document
    intent; since matching happens against the already-canonicalized hourly
    grid (not raw irregular timestamps), any positive tolerance up to half an
    hour is equivalent — exact-hour lookup.
    """
    if match_tolerance_minutes < 0:
        raise ValueError("match_tolerance_minutes must be non-negative")

    target_rows = {
        h.hour_utc: h.value
        for h in hourly
        if h.station_uuid == target_station_uuid and not h.is_missing
    }

    out = pd.DataFrame(index=issue_times)
    out.index.name = "issue_time_utc"
    for horizon in horizons_hours:
        delta = timedelta(hours=horizon)
        out[f"target_level_{horizon}h"] = [target_rows.get(t + delta) for t in issue_times]
    return out
