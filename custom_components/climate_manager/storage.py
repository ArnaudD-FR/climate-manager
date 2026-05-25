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

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_CONFIG, STORAGE_KEY, STORAGE_VERSION, _DEFAULT_DAILY_PROGRAM


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
        # For nested dicts (e.g. "period_temperatures"), merge keys individually so
        # a stored partial dict does not silently drop keys absent from the stored data.
        # Top-level scalar/list keys (e.g. "global_mode", "rooms") replace defaults
        # wholesale — individual rooms are the sparse unit (D-11).
        result = copy.deepcopy(DEFAULT_CONFIG)
        for key, value in stored.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key].update(value)  # merge nested dicts key-by-key
            else:
                result[key] = value

        # Post-merge fill: seed any day that has no periods with the default schedule.
        # This handles existing stored configs where days were saved as [] before
        # default periods were introduced.
        time_program = result.get("global_time_program", {})
        for day, periods in time_program.items():
            if not periods:
                time_program[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM.get(day, _DEFAULT_DAILY_PROGRAM["mon"]))

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

        Never uses open(), json.load, or json.dump (Pitfall 2).
        """
        await self._store.async_save(config)
