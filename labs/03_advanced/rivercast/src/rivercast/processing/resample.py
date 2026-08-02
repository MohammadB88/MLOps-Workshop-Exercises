"""Resample canonical observations onto the hourly grid (PLAN.md Phase 4).

Rule: for each target hour ``h``, use the last valid reading at or before
``h`` within ``resample_tolerance_minutes``. If no reading falls in that
window, the hour is explicit missing (``is_missing=True``, ``value=None``) —
never interpolated. Raw native-cadence data is not touched; this only builds
the derived hourly view.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timedelta

from rivercast.contracts.hourly import CanonicalObservation, HourlyObservation


def _hour_floor(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def hourly_grid(start_hour: datetime, end_hour: datetime) -> list[datetime]:
    """Inclusive hourly grid from ``start_hour`` to ``end_hour`` (both on the hour)."""
    if start_hour != _hour_floor(start_hour) or end_hour != _hour_floor(end_hour):
        raise ValueError("start_hour and end_hour must fall exactly on the hour")
    if end_hour < start_hour:
        raise ValueError(f"end_hour {end_hour} is before start_hour {start_hour}")
    hours = []
    current = start_hour
    while current <= end_hour:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def resample_hourly(
    observations: list[CanonicalObservation],
    station_uuid: str,
    station_name: str,
    parameter: str,
    start_hour: datetime,
    end_hour: datetime,
    tolerance_minutes: float,
) -> list[HourlyObservation]:
    """Resample one station/parameter's observations onto ``[start_hour, end_hour]``."""
    series = sorted(
        (
            obs
            for obs in observations
            if obs.station_uuid == station_uuid and obs.parameter == parameter
        ),
        key=lambda obs: obs.observed_at_utc,
    )
    timestamps = [obs.observed_at_utc for obs in series]
    tolerance = timedelta(minutes=tolerance_minutes)

    result: list[HourlyObservation] = []
    for hour in hourly_grid(start_hour, end_hour):
        # Rightmost reading with observed_at_utc <= hour.
        idx = bisect_right(timestamps, hour) - 1
        if idx >= 0 and hour - timestamps[idx] <= tolerance:
            reading = series[idx]
            result.append(
                HourlyObservation(
                    station_uuid=station_uuid,
                    station_name=station_name,
                    parameter=parameter,
                    hour_utc=hour,
                    value=reading.value,
                    is_missing=False,
                    source_lag_minutes=(hour - reading.observed_at_utc).total_seconds() / 60.0,
                )
            )
        else:
            result.append(
                HourlyObservation(
                    station_uuid=station_uuid,
                    station_name=station_name,
                    parameter=parameter,
                    hour_utc=hour,
                    value=None,
                    is_missing=True,
                    source_lag_minutes=None,
                )
            )
    return result
