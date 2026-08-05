"""Retention reporting for the ``bronze`` and ``predictions`` zones
(PLAN.md Phase 15 "object-store lifecycle policy" / "retention policy for
raw and prediction data").

This module is deliberately report-only: it identifies which objects are
older than a configured retention window and returns them, but never
deletes anything itself. ``ObjectStore`` has no delete primitive by design
-- raw data is immutable (CLAUDE.md rule 9), and predictions are
append-only records later extended (never rewritten) with their matured
outcome (``rivercast.contracts.predictions``). Actually removing aged-out
objects is an operator decision with real consequences (losing the ability
to recompute delayed metrics, breaking a dataset manifest's lineage back to
its raw sources) that this lab leaves to a human running the report and
deleting the listed keys through the storage backend directly, not to an
automated script with a delete button.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from rivercast.storage.object_store import ObjectStore

_BRONZE_EVENT_DATE = re.compile(r"event_date=(\d{4}-\d{2}-\d{2})")
_PREDICTIONS_ISSUED_AT = re.compile(r"issued_at=(\d{8}T\d{6}Z)")


@dataclass(frozen=True)
class RetentionCandidate:
    key: str
    as_of_date: str  # the date parsed from the key, for the report to show its work


@dataclass(frozen=True)
class RetentionReport:
    zone: str
    retention_days: int
    generated_at_utc: str
    total_keys_scanned: int
    candidates: list[RetentionCandidate]

    @property
    def eligible_for_deletion(self) -> int:
        return len(self.candidates)


def _parse_bronze_date(key: str) -> datetime | None:
    match = _BRONZE_EVENT_DATE.search(key)
    if match is None:
        return None
    return datetime.fromisoformat(match.group(1)).replace(tzinfo=UTC)


def _parse_predictions_date(key: str) -> datetime | None:
    match = _PREDICTIONS_ISSUED_AT.search(key)
    if match is None:
        return None
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


_PARSERS = {
    "bronze": _parse_bronze_date,
    "predictions": _parse_predictions_date,
}


def build_retention_report(
    store: ObjectStore,
    zone: str,
    zone_prefix: str,
    *,
    retention_days: int,
    now: datetime | None = None,
) -> RetentionReport:
    """List objects in ``zone`` (rooted at ``zone_prefix``) older than
    ``retention_days``.

    Fails closed (rule 13): a key whose date cannot be parsed is never
    silently treated as either "keep" or "delete" -- it is excluded from
    the candidate list and left for manual inspection, since guessing wrong
    on raw or prediction data is worse than doing nothing.
    """
    if zone not in _PARSERS:
        raise ValueError(
            f"retention reporting is not defined for zone {zone!r}; "
            f"expected one of {sorted(_PARSERS)}"
        )
    now = now if now is not None else datetime.now(UTC)
    parse_date = _PARSERS[zone]
    cutoff = now.timestamp() - retention_days * 86400

    keys = store.list_keys(zone_prefix)
    candidates = []
    for key in keys:
        parsed = parse_date(key)
        if parsed is None:
            continue
        if parsed.timestamp() < cutoff:
            candidates.append(RetentionCandidate(key=key, as_of_date=parsed.date().isoformat()))

    return RetentionReport(
        zone=zone,
        retention_days=retention_days,
        generated_at_utc=now.isoformat(timespec="seconds"),
        total_keys_scanned=len(keys),
        candidates=sorted(candidates, key=lambda c: c.key),
    )
