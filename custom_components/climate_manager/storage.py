"""Climate Manager storage layer.

Provides ClimateManagerStore: a thin wrapper around HA's Store helper
that implements sparse-merge loading over DEFAULT_CONFIG and async save.

Design decisions (from RESEARCH.md):
- Pattern 3: Store with schema version and sparse defaults
- Pitfall 2: Never use open()/json.load/json.dump — all I/O via Store
- Pitfall 3: Schema goes here, NOT in ConfigEntry.options
- Note: serialize_in_event_loop parameter not present in HA 2024.x Store
  (was added in later HA core; use default Store constructor for compatibility)
"""

import copy
import uuid  # D-07: UUID generation for zone IDs

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_CONFIG,
    STORAGE_KEY,
    STORAGE_VERSION,
    _DEFAULT_DAILY_PROGRAM,
)


_SENTINEL = (
    object()
)  # sentinel for distinguishing absent key from explicit None (WR-01)


def validate_zone_assignment(config: dict) -> None:
    """Raise ValueError if zone assignment invariants are violated (ZONE-04).

    Checks:
    1. Every zone_id on a room entry references an existing zone in config["zones"].
    2. Explicit zone_id: null is rejected — sparse model prohibits it (D-06/WR-01).

    Returns None silently when configuration is valid OR when every room lacks a
    zone_id key (Default Zone membership per D-06).

    Tolerates absent 'zones' and 'rooms' keys by treating them as empty dicts.

    Called by async_save() before persisting. Phase 5 WebSocket handlers may also
    import and call this directly before triggering save.

    Note: ZONE-04 ("a room belongs to at most one zone") is structurally guaranteed
    by the rooms dict being keyed by area_id — each room appears exactly once.
    No seen_zone_ids check is needed; multiple rooms may share the same zone_id.
    """
    zones = config.get("zones", {})
    for area_id, room_cfg in config.get("rooms", {}).items():
        zone_id = room_cfg.get("zone_id", _SENTINEL)
        if zone_id is _SENTINEL:
            continue  # D-06: absent zone_id = Default Zone member — valid
        if zone_id is None:
            raise ValueError(
                f"Room '{area_id}' has zone_id: null"
                " — sparse model prohibits explicit null (D-06)"
            )
        if zone_id not in zones:
            raise ValueError(
                f"Room '{area_id}' references unknown zone_id '{zone_id}'"
            )


class ClimateManagerStore:
    """Manages persistence of the Climate Manager configuration.

    Wraps homeassistant.helpers.storage.Store.
    - async_load(): Returns DEFAULT_CONFIG merged with any stored sparse data.
      Fresh install (no stored data) returns a deep copy of DEFAULT_CONFIG.
    - async_save(config): Persists config via the Store helper.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store wrapper."""
        self._store = Store(
            hass,
            version=STORAGE_VERSION,
            key=STORAGE_KEY,
        )

    async def async_load(self) -> dict:
        """Load and return the merged configuration.

        Merges stored sparse data over a deep copy of DEFAULT_CONFIG so that:
        - Fresh installs get full defaults (no mutation risk).
        - Stored overrides win at the top level (sparse storage model — D-11).
        - Unset top-level keys fall back to defaults automatically.

        Post-merge fill: any day in global_time_program that has an empty period
        list (never configured) receives the default day periods so that the
        time-bar is pre-populated on first use.
        """
        stored = await self._store.async_load()
        if stored is None:
            # Fresh install: return a deep copy so callers cannot mutate DEFAULT_CONFIG
            return copy.deepcopy(DEFAULT_CONFIG)
        # Sparse deep-merge: deep-copy defaults first, then overlay stored values.
        # Only "period_temperatures" uses key-by-key merging because it is the one
        # nested dict where stored data may be a partial sub-dict (missing keys fall
        # back to defaults).  All collection keys ("rooms", "persons", "zones") are
        # replaced wholesale — the stored value IS the full collection, not a diff.
        # This prevents a non-empty DEFAULT_CONFIG["rooms"/"zones"/"persons"] from
        # ever accidentally merging with stored data (CR-02 guard).
        result = copy.deepcopy(DEFAULT_CONFIG)
        for key, value in stored.items():
            if (
                key in ("period_temperatures",)
                and isinstance(value, dict)
                and isinstance(result.get(key), dict)
            ):
                # Only period_temperatures needs key-by-key merge (partial stored sub-dict).
                # rooms, persons, zones are replaced wholesale — the stored value IS the full collection.
                result[key].update(value)
            else:
                result[key] = value

        # Post-merge fill: seed any day that has no periods with the default schedule.
        # This handles existing stored configs where days were saved as [] before
        # default periods were introduced.
        time_program = result.get("global_time_program", {})
        for day, periods in time_program.items():
            if not periods:
                time_program[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])

        # Migration: rename person presence modes to current wire values.
        for person_cfg in result.get("persons", {}).values():
            # Pre-D-21: "automatic" → "scheduled"
            if person_cfg.get("mode") == "automatic":
                person_cfg["mode"] = "scheduled"
            # D-21: "present" → "force_present", "absent" → "force_absent"
            elif person_cfg.get("mode") == "present":
                person_cfg["mode"] = "force_present"
            elif person_cfg.get("mode") == "absent":
                person_cfg["mode"] = "force_absent"

        return result

    async def async_save(self, config: dict) -> None:
        """Persist the configuration via the Store helper.

        Validates zone assignment invariants (ZONE-04) before writing.
        Never uses open(), json.load, or json.dump (Pitfall 2).
        """
        validate_zone_assignment(config)
        await self._store.async_save(config)
