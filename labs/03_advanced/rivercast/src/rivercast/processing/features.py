"""Leakage-safe feature generation from hourly canonical observations (PLAN.md Phase 5).

At issue time ``t`` (one row per hour on the target station's grid), every
feature is computed from observations with ``hour_utc <= t`` only:

- lags and rolling statistics are backward-looking windows that *end* at ``t``;
- calendar features are pure functions of ``t`` itself;
- missingness indicators reflect whether the source hourly grid had data at
  or before ``t``.

No feature column may read a value at ``hour_utc > t`` for any station,
including the target. That invariant is enforced structurally here (only
``shift``/backward ``rolling`` are used, both by construction non-anticipating)
and re-verified by the mandatory leakage tests in
``tests/unit/test_leakage.py``.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from rivercast.contracts.hourly import HourlyObservation

LAG_HOURS = (1, 3, 6)
ROLLING_WINDOW_HOURS = 6


def _to_frame(hourly: list[HourlyObservation], station_uuid: str) -> pd.DataFrame:
    rows = [h for h in hourly if h.station_uuid == station_uuid]
    if not rows:
        raise ValueError(f"no hourly observations for station {station_uuid}")
    frame = pd.DataFrame(
        {
            "hour_utc": [h.hour_utc for h in rows],
            "value": [h.value for h in rows],
        }
    ).sort_values("hour_utc")
    if frame["hour_utc"].duplicated().any():
        raise ValueError(f"duplicate hour_utc entries for station {station_uuid}")
    return frame.set_index("hour_utc")


def _station_features(
    hourly: list[HourlyObservation], station_uuid: str, prefix: str
) -> pd.DataFrame:
    """Backward-looking features for one station; index is the issue-time hour."""
    frame = _to_frame(hourly, station_uuid)
    value = frame["value"]

    out = pd.DataFrame(index=frame.index)
    out[f"{prefix}_level_t"] = value
    for lag in LAG_HOURS:
        # shift(lag): value from `lag` hours before the current row's own hour
        # -- strictly <= t, never anticipates the future.
        out[f"{prefix}_lag_{lag}h"] = value.shift(lag)
    out[f"{prefix}_delta_1h"] = value - value.shift(1)
    out[f"{prefix}_delta_6h"] = value - value.shift(ROLLING_WINDOW_HOURS)
    # rolling(...) over a datetime-sorted series is backward-looking by
    # default (the window ending at the current row); min_periods=1 so an
    # incomplete warm-up window still yields a (partial) statistic rather
    # than silently peeking past t.
    out[f"{prefix}_roll_mean_6h"] = value.rolling(ROLLING_WINDOW_HOURS, min_periods=1).mean()
    out[f"{prefix}_roll_std_6h"] = value.rolling(ROLLING_WINDOW_HOURS, min_periods=1).std()
    out[f"missing_{prefix}"] = value.isna().astype(int)
    return out


def _calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Pure functions of the issue time itself — never a data lookup."""
    hour = index.hour.to_numpy()
    day_of_year = index.dayofyear.to_numpy()
    return pd.DataFrame(
        {
            "hour_sin": np.sin(2 * math.pi * hour / 24),
            "hour_cos": np.cos(2 * math.pi * hour / 24),
            "day_of_year_sin": np.sin(2 * math.pi * day_of_year / 365.25),
            "day_of_year_cos": np.cos(2 * math.pi * day_of_year / 365.25),
        },
        index=index,
    )


def build_features(
    hourly: list[HourlyObservation],
    target_station_uuid: str,
    upstream_station_uuids: list[str],
    station_prefixes: dict[str, str],
) -> pd.DataFrame:
    """Build the leakage-safe feature table, one row per issue-time hour.

    ``station_prefixes`` maps station UUID to its column prefix (e.g.
    ``{kaub_uuid: "kaub", bingen_uuid: "bingen"}``); every station in
    ``[target_station_uuid, *upstream_station_uuids]`` must have an entry.
    """
    all_stations = [target_station_uuid, *upstream_station_uuids]
    missing_prefixes = [s for s in all_stations if s not in station_prefixes]
    if missing_prefixes:
        raise ValueError(f"no column prefix configured for station(s): {missing_prefixes}")

    parts = [_station_features(hourly, uuid, station_prefixes[uuid]) for uuid in all_stations]
    combined: pd.DataFrame = (
        parts[0].join(list(parts[1:]), how="outer") if len(parts) > 1 else parts[0]
    )
    index: pd.DatetimeIndex = pd.DatetimeIndex(combined.index)
    combined = combined.join(_calendar_features(index))
    combined.index.name = "issue_time_utc"
    return combined.sort_index()
