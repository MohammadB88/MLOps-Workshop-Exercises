"""Production adapter for the stable PEGELONLINE REST API.

Endpoints and behavior verified by the Phase 2 spike
(``docs/data_viability_report.md``): anonymous access, ~31-day measurement
window, 15-minute cadence, ISO-8601 timestamps with explicit offsets.

Every request has a timeout and bounded exponential-backoff retry from
configuration (rule 4). The HTTP transport is injectable so unit tests
exercise retry/timeout/error paths with zero network access (rule 3).
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from rivercast.config import SourceConfig
from rivercast.contracts.raw import RawFetch, RawFetchMetadata, Station
from rivercast.gitinfo import current_commit
from rivercast.log import get_logger
from rivercast.sources.base import MalformedResponseError, SourceError, SourceTimeoutError

_LOG = get_logger("sources.pegelonline")

USER_AGENT = "rivercast/0.1 (MLOps workshop, educational)"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


Transport = Callable[[str, dict[str, str], float], HttpResponse]
"""``(url, headers, timeout_seconds) -> HttpResponse``; raises OSError-family on failure."""


def _urllib_transport(url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return HttpResponse(
            status=response.status,
            headers={k.lower(): v for k, v in response.headers.items()},
            body=response.read(),
        )


class PegelOnlineSource:
    """Live gauge source; implements the :class:`~rivercast.sources.base.GaugeSource` protocol."""

    source_name = "pegelonline-rest-v2"

    def __init__(self, config: SourceConfig, transport: Transport | None = None) -> None:
        self._config = config
        self._transport = transport if transport is not None else _urllib_transport

    # -- HTTP with retry ---------------------------------------------------

    def _get(self, url: str) -> HttpResponse:
        retry = self._config.retry
        delay = retry.backoff_initial_seconds
        last_error: Exception | None = None
        for attempt in range(1, retry.max_attempts + 1):
            try:
                response = self._transport(
                    url, {"User-Agent": USER_AGENT}, self._config.request_timeout_seconds
                )
            except urllib.error.HTTPError as exc:  # HTTP status >= 400
                if 500 <= exc.code < 600 and attempt < retry.max_attempts:
                    last_error = exc
                else:
                    raise SourceError(
                        f"GET {url} failed with HTTP {exc.code}: {exc.reason}"
                    ) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_error = exc
            else:
                if response.status == 200:
                    return response
                raise SourceError(f"GET {url} returned unexpected HTTP {response.status}")
            if attempt < retry.max_attempts:
                _LOG.warning(
                    "request failed, retrying",
                    extra={"url": url, "attempt": attempt, "delay_seconds": delay},
                )
                time.sleep(delay)
                delay = min(delay * 2, retry.backoff_max_seconds)
        raise SourceTimeoutError(
            f"GET {url} failed after {retry.max_attempts} attempts "
            f"(timeout {self._config.request_timeout_seconds}s): {last_error}"
        )

    # -- GaugeSource protocol ----------------------------------------------

    def list_stations(self, water: str) -> list[Station]:
        url = f"{self._config.base_url}/stations.json?waters={urllib.parse.quote(water)}"
        response = self._get(url)
        try:
            entries: Any = json.loads(response.body)
        except json.JSONDecodeError as exc:
            raise MalformedResponseError(
                f"station list from {url} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(entries, list):
            raise MalformedResponseError(f"station list from {url} is not a JSON array")
        stations = []
        for entry in entries:
            stations.append(
                Station(
                    uuid=entry["uuid"],
                    shortname=entry["shortname"],
                    water=entry.get("water", {}).get("shortname", water),
                    km=entry.get("km"),
                    number=str(entry["number"]) if entry.get("number") is not None else None,
                    agency=entry.get("agency"),
                )
            )
        return stations

    def fetch_raw(
        self,
        station_uuid: str,
        parameter: str,
        start: datetime,
        end: datetime,
    ) -> RawFetch:
        if start.tzinfo is None or end.tzinfo is None:
            raise SourceError("start and end must be timezone-aware")
        start_iso = start.astimezone(UTC).isoformat()
        end_iso = end.astimezone(UTC).isoformat()
        url = (
            f"{self._config.base_url}/stations/{station_uuid}/{urllib.parse.quote(parameter)}"
            f"/measurements.json?start={urllib.parse.quote(start_iso)}"
            f"&end={urllib.parse.quote(end_iso)}"
        )
        response = self._get(url)
        metadata = RawFetchMetadata(
            source=self.source_name,
            station_uuid=station_uuid,
            parameter=parameter,
            requested_start=start_iso,
            requested_end=end_iso,
            fetched_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
            http_status=response.status,
            etag=response.headers.get("etag"),
            sha256=hashlib.sha256(response.body).hexdigest(),
            code_commit=current_commit(),
        )
        _LOG.info(
            "fetched raw measurements",
            extra={
                "station_uuid": station_uuid,
                "parameter": parameter,
                "bytes": len(response.body),
                "sha256": metadata.sha256[:12],
            },
        )
        return RawFetch(payload=response.body, metadata=metadata)
