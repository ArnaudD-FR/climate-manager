"""Climate Manager constants and default configuration schema.

This module is the single source of truth for all domain constants
and the v2 storage schema. All other modules import from here.
No Home Assistant imports — pure constants only.
"""

import copy

# ---------------------------------------------------------------------------
# Core identifiers
# ---------------------------------------------------------------------------

DOMAIN = "climate_manager"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 2

# ---------------------------------------------------------------------------
# Global mode constants
# ---------------------------------------------------------------------------

MODE_OFF = "off"
MODE_TIME_PROGRAM = "time_program"
MODE_TIME_PROGRAM_PRESENCES = "time_program_presences"

# ---------------------------------------------------------------------------
# Period mode name constants
# ---------------------------------------------------------------------------

PERIOD_FROST_PROTECTION = "frost_protection"
PERIOD_REDUCED = "reduced"
PERIOD_NORMAL = "normal"
PERIOD_COMFORT = "comfort"

# ---------------------------------------------------------------------------
# Presence mode constants (PERSON-01; Pitfall 7 — define before use in schedule.py)
# ---------------------------------------------------------------------------

PRESENCE_AUTOMATIC = "automatic"
PRESENCE_PRESENT = "present"
PRESENCE_ABSENT = "absent"

# ---------------------------------------------------------------------------
# Per-room mode constants (D-20)
# ---------------------------------------------------------------------------

ROOM_MODE_GLOBAL = "global"
ROOM_MODE_FROST = "frost_protection"
ROOM_MODE_CUSTOM = "custom"

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULT_GLOBAL_MODE = MODE_TIME_PROGRAM

DEFAULT_PERIOD_TEMPERATURES: dict[str, float] = {
    PERIOD_FROST_PROTECTION: 7.0,   # GLOBAL-03
    PERIOD_REDUCED: 18.0,            # GLOBAL-03
    PERIOD_NORMAL: 20.0,             # GLOBAL-03
    PERIOD_COMFORT: 22.0,            # GLOBAL-03
}

# ---------------------------------------------------------------------------
# Per-day schema helpers (D-01)
# ---------------------------------------------------------------------------

_DAYS_ORDERED = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Default daily schedule: reduced overnight, normal during the day.
#   00:00 – 06:00  reduced
#   06:00 – 22:00  normal
#   22:00 – 24:00  reduced  (implicit: last period runs to midnight)
_DEFAULT_DAY_PERIODS: list[dict] = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "06:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]

_DEFAULT_DAILY_PROGRAM: dict = {
    day: copy.deepcopy(_DEFAULT_DAY_PERIODS) for day in _DAYS_ORDERED
}

# ---------------------------------------------------------------------------
# Full v2 storage schema with defaults (D-01, D-09, D-10, D-11)
#
# Sparse storage: only values that differ from these defaults are written.
#
# Rooms sub-schema (keyed by area_id from HA area registry — D-13):
#   {
#     "<area_id>": {
#       "time_program": {
#         "mon": [{"start": "HH:MM", "mode": "<period_mode>"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       },
#       "temperature_sensor": "<entity_id>",   # optional (D-16) — string entity ID
#       "humidity_sensor": "<entity_id>"        # optional (D-16) — string entity ID
#     }
#   }
#   Empty dict = all rooms inherit the global time program.
#   A room entry only appears if it has a non-default (custom) time program.
#
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",   # "automatic" | "present" | "absent"
#       "room_ids": ["<area_id>", ...],
#       "schedule": {
#         "mon": [{"start": "HH:MM", "state": "present"|"absent"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       }
#     }
#   }
#   Empty dict = all persons at default (Automatic mode, no schedule, no rooms).
#   A person entry only appears if it has at least one non-default setting.
#
# Note: area.name and person friendly_name are NOT cached here —
#       they are read fresh from HA registries at display time to avoid staleness
#       if the user renames an area or person in HA (RESEARCH Open Questions 1 & 2).
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": {
        PERIOD_FROST_PROTECTION: 7.0,
        PERIOD_REDUCED: 18.0,
        PERIOD_NORMAL: 20.0,
        PERIOD_COMFORT: 22.0,
    },
    "global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "rooms": {},    # sparse: only rooms with non-default config (SCHED-05, D-11)
    "persons": {},  # sparse: only persons with non-default settings (D-11)
}
