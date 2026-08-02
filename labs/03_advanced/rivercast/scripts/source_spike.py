"""Phase 2 data-viability spike for PEGELONLINE (PLAN.md Phase 2).

Reusable module behind ``notebooks/01_source_and_data_quality.ipynb``. Spike
code, not production: the Phase 3 source adapters supersede the fetch helpers
here. The *analysis* functions are pure and deterministic so the notebook can
run them offline against committed fixtures.

Endpoints (verified 2026-08-02, no credentials required):

- Stable REST API (live, last ~31 days, 15-min cadence):
  ``https://www.pegelonline.wsv.de/webservices/rest-api/v2``
- Historical raw data since 2000-01-01 (unvalidated), synchronous zip download:
  ``POST https://www.pegelonline.wsv.de/gast/historische-zeitreihen/prepare-download``
  with form fields ``uuid``, ``parameter="WASSERSTAND ROHDATEN"``, ``start``,
  ``end`` (ISO-8601), ``format=json``.
- HyDAS API is beta and only serves recent data — evaluation-only (plan §2).

Usage (live fetch; writes fixtures and the live-results summary):

    python scripts/source_spike.py --live

Offline analysis of committed fixtures (what the notebook does):

    python scripts/source_spike.py
"""

from __future__ import annotations

import argparse
import io
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

STABLE_API = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
HISTORICAL_ENDPOINT = "https://www.pegelonline.wsv.de/gast/historische-zeitreihen/prepare-download"
USER_AGENT = "rivercast-source-spike/0.1 (MLOps workshop, educational)"
REQUEST_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
POLITENESS_DELAY_SECONDS = 0.5

EXPECTED_CADENCE_MINUTES = 15.0
GAP_TOLERANCE_MINUTES = 20.0

# Historical sample windows (fixed so fixtures are reproducible).
OVERLAP_WINDOW = ("2024-08-01T00:00:00+02:00", "2024-08-08T00:00:00+02:00")  # all stations
DST_SPRING_WINDOW = ("2025-03-29T12:00:00+01:00", "2025-03-31T00:00:00+02:00")  # KAUB
DST_FALL_WINDOW = ("2025-10-25T12:00:00+02:00", "2025-10-27T00:00:00+01:00")  # KAUB
EARLIEST_WINDOW = ("2000-01-01T00:00:00+01:00", "2000-01-04T00:00:00+01:00")  # KAUB
RECENT_FIXTURE_DAYS = 7


# ---------------------------------------------------------------------------
# Fetch helpers (live mode only; the notebook default never calls these)
# ---------------------------------------------------------------------------


def _request_bytes(url: str, form: dict[str, str] | None = None) -> bytes:
    data = urllib.parse.urlencode(form).encode("ascii") if form is not None else None
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"request failed after {MAX_ATTEMPTS} attempts: {url}: {last_error}")


def fetch_json(url: str) -> Any:
    return json.loads(_request_bytes(url))


def list_stations(water: str = "RHEIN") -> list[dict[str, Any]]:
    return fetch_json(f"{STABLE_API}/stations.json?waters={urllib.parse.quote(water)}")


def fetch_recent_measurements(station_uuid: str, period: str = "P31D") -> list[dict[str, Any]]:
    url = f"{STABLE_API}/stations/{station_uuid}/W/measurements.json?start={period}"
    return fetch_json(url)


def fetch_station_with_current(station_uuid: str) -> dict[str, Any]:
    url = (
        f"{STABLE_API}/stations/{station_uuid}.json"
        "?includeTimeseries=true&includeCurrentMeasurement=true"
    )
    return fetch_json(url)


def fetch_historical(station_uuid: str, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    """Download a historical window as JSON via the synchronous zip endpoint."""
    payload = _request_bytes(
        HISTORICAL_ENDPOINT,
        form={
            "uuid": station_uuid,
            "parameter": "WASSERSTAND ROHDATEN",
            "start": start_iso,
            "end": end_iso,
            "format": "json",
        },
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        # Alongside the data the zip carries nutzungsbedingungen.txt and
        # zeitreiheninformation.txt; the measurements are the one .json member.
        json_members = [n for n in archive.namelist() if n.endswith(".json")]
        if len(json_members) != 1:
            raise RuntimeError(
                f"expected one .json member in historical zip, got {archive.namelist()}"
            )
        rows = json.loads(archive.read(json_members[0]))
    if not isinstance(rows, list):
        raise RuntimeError(f"historical payload is not a JSON array ({type(rows).__name__})")
    return rows


# ---------------------------------------------------------------------------
# Pure analysis (used offline by notebook and tests)
# ---------------------------------------------------------------------------


def parse_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without offset: {raw!r}")
    return parsed


@dataclass(frozen=True)
class SeriesStats:
    rows: int
    first_utc: str | None
    last_utc: str | None
    cadence_minutes_mode: float | None
    cadence_histogram: dict[str, int]
    gaps_over_tolerance: int
    max_gap_minutes: float
    duplicate_timestamps: int
    conflicting_duplicates: int
    non_monotonic_steps: int
    value_min: float | None
    value_max: float | None
    utc_offsets_seen: list[str]


def analyze_series(
    rows: list[dict[str, Any]],
    gap_tolerance_minutes: float = GAP_TOLERANCE_MINUTES,
) -> SeriesStats:
    if not rows:
        return SeriesStats(0, None, None, None, {}, 0, 0.0, 0, 0, 0, None, None, [])

    parsed: list[tuple[datetime, float]] = []
    offsets: set[str] = set()
    for row in rows:
        ts = parse_timestamp(row["timestamp"])
        offset = ts.utcoffset()
        assert offset is not None
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        offsets.add(f"{sign}{abs(total_minutes) // 60:02d}:{abs(total_minutes) % 60:02d}")
        parsed.append((ts.astimezone(UTC), float(row["value"])))

    by_ts: dict[datetime, set[float]] = {}
    for ts, value in parsed:
        by_ts.setdefault(ts, set()).add(value)
    duplicate_timestamps = len(parsed) - len(by_ts)
    conflicting = sum(1 for values in by_ts.values() if len(values) > 1)

    non_monotonic = sum(1 for a, b in zip(parsed, parsed[1:], strict=False) if b[0] <= a[0])

    unique_sorted = sorted(by_ts)
    deltas = [
        (b - a).total_seconds() / 60.0
        for a, b in zip(unique_sorted, unique_sorted[1:], strict=False)
    ]
    histogram = Counter(f"{delta:g}min" for delta in deltas)
    mode_delta = statistics.mode(deltas) if deltas else None

    values = [value for _, value in parsed]
    return SeriesStats(
        rows=len(rows),
        first_utc=unique_sorted[0].isoformat(),
        last_utc=unique_sorted[-1].isoformat(),
        cadence_minutes_mode=mode_delta,
        cadence_histogram=dict(histogram.most_common(6)),
        gaps_over_tolerance=sum(1 for delta in deltas if delta > gap_tolerance_minutes),
        max_gap_minutes=max(deltas) if deltas else 0.0,
        duplicate_timestamps=duplicate_timestamps,
        conflicting_duplicates=conflicting,
        non_monotonic_steps=non_monotonic,
        value_min=min(values),
        value_max=max(values),
        utc_offsets_seen=sorted(offsets),
    )


def overlap_stats(series_by_name: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Coverage of each station inside the common (intersection) window."""
    spans: dict[str, tuple[datetime, datetime, dict[datetime, float]]] = {}
    for name, rows in series_by_name.items():
        stamps = {parse_timestamp(r["timestamp"]).astimezone(UTC): float(r["value"]) for r in rows}
        if not stamps:
            return {"common_window": None, "note": f"station {name} has no rows"}
        spans[name] = (min(stamps), max(stamps), stamps)

    common_start = max(start for start, _, _ in spans.values())
    common_end = min(end for _, end, _ in spans.values())
    if common_end <= common_start:
        return {"common_window": None, "note": "no overlapping window"}

    expected = int((common_end - common_start).total_seconds() / 60 / EXPECTED_CADENCE_MINUTES) + 1
    coverage = {
        name: round(sum(1 for ts in stamps if common_start <= ts <= common_end) / expected, 4)
        for name, (_, _, stamps) in spans.items()
    }
    return {
        "common_window": [common_start.isoformat(), common_end.isoformat()],
        "expected_grid_points": expected,
        "coverage_fraction": coverage,
    }


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("need equal-length series with at least 3 points")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        return 0.0
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / denom


def upstream_lead_correlation(
    target_rows: list[dict[str, Any]],
    upstream_rows: list[dict[str, Any]],
    lead_hours: int = 6,
) -> dict[str, Any]:
    """Correlate the target's future change with current changes (spike question:
    does upstream information carry signal a persistence baseline lacks?).

    ``future_target_delta(t)  = target(t + lead) - target(t)`` is correlated with
    ``upstream_delta(t)       = upstream(t) - upstream(t - lead)`` and, as the
    persistence-style reference, with ``target_delta(t) = target(t) - target(t - lead)``.
    Uses only information at or before ``t`` on the predictor side.
    """
    lead = timedelta(hours=lead_hours)
    target = {
        parse_timestamp(r["timestamp"]).astimezone(UTC): float(r["value"]) for r in target_rows
    }
    upstream = {
        parse_timestamp(r["timestamp"]).astimezone(UTC): float(r["value"]) for r in upstream_rows
    }
    future_deltas: list[float] = []
    upstream_deltas: list[float] = []
    target_deltas: list[float] = []
    for ts, value in target.items():
        if ts + lead in target and ts - lead in target and ts in upstream and ts - lead in upstream:
            future_deltas.append(target[ts + lead] - value)
            upstream_deltas.append(upstream[ts] - upstream[ts - lead])
            target_deltas.append(value - target[ts - lead])
    if len(future_deltas) < 3:
        return {"n": len(future_deltas), "note": "insufficient aligned points"}
    return {
        "n": len(future_deltas),
        "lead_hours": lead_hours,
        "corr_upstream_delta_vs_future": round(pearson(upstream_deltas, future_deltas), 4),
        "corr_own_delta_vs_future": round(pearson(target_deltas, future_deltas), 4),
    }


# ---------------------------------------------------------------------------
# Fixture IO
# ---------------------------------------------------------------------------


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


# ---------------------------------------------------------------------------
# Spike orchestration
# ---------------------------------------------------------------------------


def _station_names(lab_root: Path) -> tuple[list[str], str]:
    sys.path.insert(0, str(lab_root / "src"))
    from rivercast.config import load_config  # spike-only late import

    config = load_config(lab_root / "configs" / "local.yaml")
    return [s.name for s in config.stations], config.target_station


def run_live_spike(lab_root: Path) -> dict[str, Any]:
    """Fetch live data, write deterministic fixtures, return the live summary."""
    names, target_name = _station_names(lab_root)
    out = fixture_dir(lab_root)
    fetched_at = datetime.now(UTC).isoformat(timespec="seconds")

    print("[spike] listing RHEIN stations ...")
    stations = list_stations("RHEIN")
    trimmed = [
        {k: s.get(k) for k in ("uuid", "number", "shortname", "km", "agency")}
        for s in sorted(stations, key=lambda s: s.get("km") or 0)
    ]
    save_json(out / "stations_rhein.json", trimmed)

    by_name = {s["shortname"]: s for s in stations}
    missing = [n for n in names if n not in by_name]
    if missing:
        raise RuntimeError(f"configured stations not found on PEGELONLINE: {missing}")
    resolved = {n: by_name[n] for n in names}

    summary: dict[str, Any] = {
        "fetched_at_utc": fetched_at,
        "stations": {
            n: {"uuid": s["uuid"], "number": s.get("number"), "km": s.get("km")}
            for n, s in resolved.items()
        },
        "recent_31d": {},
        "latency_minutes": {},
    }

    for name, station in resolved.items():
        time.sleep(POLITENESS_DELAY_SECONDS)
        print(f"[spike] {name}: fetching 31d of W measurements ...")
        rows = fetch_recent_measurements(station["uuid"])
        summary["recent_31d"][name] = asdict(analyze_series(rows))

        cutoff = datetime.now(UTC) - timedelta(days=RECENT_FIXTURE_DAYS)
        recent_fixture = [
            r for r in rows if parse_timestamp(r["timestamp"]).astimezone(UTC) >= cutoff
        ]
        save_json(out / "recent" / f"{name}.json", recent_fixture)

        time.sleep(POLITENESS_DELAY_SECONDS)
        detail = fetch_station_with_current(station["uuid"])
        for series in detail.get("timeseries", []):
            if series.get("shortname") == "W" and series.get("currentMeasurement"):
                current_ts = parse_timestamp(series["currentMeasurement"]["timestamp"])
                age = datetime.now(UTC) - current_ts.astimezone(UTC)
                summary["latency_minutes"][name] = round(age.total_seconds() / 60, 1)

    print("[spike] fetching historical overlap window for all stations ...")
    for name, station in resolved.items():
        time.sleep(POLITENESS_DELAY_SECONDS)
        rows = fetch_historical(station["uuid"], *OVERLAP_WINDOW)
        save_json(out / "historical" / "overlap_2024-08" / f"{name}.json", rows)

    target_uuid = resolved[target_name]["uuid"]
    for label, window in (
        ("dst_spring_2025", DST_SPRING_WINDOW),
        ("dst_fall_2025", DST_FALL_WINDOW),
        ("earliest_2000", EARLIEST_WINDOW),
    ):
        time.sleep(POLITENESS_DELAY_SECONDS)
        print(f"[spike] fetching {label} window for {target_name} ...")
        rows = fetch_historical(target_uuid, *window)
        save_json(out / "historical" / f"{label}_{target_name}.json", rows)

    summary["windows"] = {
        "overlap": OVERLAP_WINDOW,
        "dst_spring": DST_SPRING_WINDOW,
        "dst_fall": DST_FALL_WINDOW,
        "earliest": EARLIEST_WINDOW,
    }
    save_json(out / "spike_live_results.json", summary)
    return summary


def analyze_fixtures(lab_root: Path) -> dict[str, Any]:
    """Deterministic offline analysis of the committed fixtures."""
    names, target_name = _station_names(lab_root)
    fixtures = fixture_dir(lab_root)

    recent = {n: load_json(fixtures / "recent" / f"{n}.json") for n in names}
    overlap = {
        n: load_json(fixtures / "historical" / "overlap_2024-08" / f"{n}.json") for n in names
    }
    report: dict[str, Any] = {
        "recent_series": {n: asdict(analyze_series(rows)) for n, rows in recent.items()},
        "recent_overlap": overlap_stats(recent),
        "historical_overlap_2024": overlap_stats(overlap),
        "historical_series_2024": {n: asdict(analyze_series(rows)) for n, rows in overlap.items()},
    }
    for label in ("dst_spring_2025", "dst_fall_2025", "earliest_2000"):
        rows = load_json(fixtures / "historical" / f"{label}_{target_name}.json")
        report[label] = asdict(analyze_series(rows))

    upstream_names = [n for n in names if n != target_name]
    report["upstream_correlation_6h"] = {
        n: upstream_lead_correlation(recent[target_name], recent[n], lead_hours=6)
        for n in upstream_names
    }
    report["auto_correlation_6h"] = upstream_lead_correlation(
        recent[target_name], recent[target_name], lead_hours=6
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--live",
        action="store_true",
        help="fetch from PEGELONLINE and (re)write fixtures; default is offline fixture analysis",
    )
    args = parser.parse_args(argv)
    lab_root = Path(__file__).resolve().parents[1]

    if args.live:
        summary = run_live_spike(lab_root)
        print(json.dumps(summary, indent=2, sort_keys=True))
    report = analyze_fixtures(lab_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
