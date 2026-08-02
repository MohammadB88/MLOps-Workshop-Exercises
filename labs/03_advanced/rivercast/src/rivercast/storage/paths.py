"""Object-key construction for the six storage zones (ADR 0002).

Phase 1 provides only the generic zone helper; phase-specific layouts
(bronze partitioning, dataset directories) are added by the phases that
own them, always through this module so key formats stay in one place.
"""

from __future__ import annotations

from rivercast.config import StorageZones
from rivercast.storage.object_store import ObjectStoreError, _validate_key

_ZONE_FIELDS = ("bronze", "silver", "gold", "predictions", "reports", "models")


def zone_key(zones: StorageZones, zone: str, *parts: str) -> str:
    """Build an object key inside a named zone, e.g. ``zone_key(z, "bronze", "a", "b.json")``."""
    if zone not in _ZONE_FIELDS:
        raise ObjectStoreError(f"unknown storage zone {zone!r}; expected one of {_ZONE_FIELDS}")
    if not parts:
        raise ObjectStoreError(f"zone_key requires at least one path part after zone {zone!r}")
    prefix: str = getattr(zones, zone)
    key = "/".join((prefix.strip("/"), *parts))
    return _validate_key(key)
