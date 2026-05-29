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
# Presence mode constants (PERSON-01; Pitfall 7 — define before use in schedule.py; D-21)
# ---------------------------------------------------------------------------

PRESENCE_AUTOMATIC = "scheduled"
PRESENCE_PRESENT = "force_present"
PRESENCE_ABSENT = "force_absent"
PRESENCE_HA = "ha"

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
    PERIOD_FROST_PROTECTION: 5.0,  # GLOBAL-03
    PERIOD_REDUCED: 18.0,  # GLOBAL-03
    PERIOD_NORMAL: 20.0,  # GLOBAL-03
    PERIOD_COMFORT: 22.0,  # GLOBAL-03
}

# ---------------------------------------------------------------------------
# Per-day schema helpers (D-01)
# ---------------------------------------------------------------------------

_DAYS_ORDERED = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
_WEEKEND = ["sat", "sun"]

# Default weekday schedule: reduced overnight, two normal blocks (morning + evening).
#   00:00 – 06:00  reduced   (night)
#   06:00 – 08:00  normal    (morning routine)
#   08:00 – 17:00  reduced   (away / work hours)
#   17:00 – 22:00  normal    (evening home)
#   22:00 – 24:00  reduced   (night)
_DEFAULT_WEEKDAY_PERIODS: list[dict] = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "06:00", "mode": PERIOD_NORMAL},
    {"start": "08:00", "mode": PERIOD_REDUCED},
    {"start": "17:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]

# Default weekend schedule: reduced overnight, normal all day.
#   00:00 – 06:00  reduced   (night)
#   06:00 – 22:00  normal    (full day home)
#   22:00 – 24:00  reduced   (night)
_DEFAULT_WEEKEND_PERIODS: list[dict] = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "06:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]

_DEFAULT_DAILY_PROGRAM: dict = {
    **{day: copy.deepcopy(_DEFAULT_WEEKDAY_PERIODS) for day in _WEEKDAYS},
    **{day: copy.deepcopy(_DEFAULT_WEEKEND_PERIODS) for day in _WEEKEND},
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
#       "humidity_sensor": "<entity_id>",       # optional (D-16) — string entity ID
#       "zone_id": "<uuid>"                     # optional string UUID — absent = belongs to Default Zone (D-05, D-06)
#                                               # Only present if room is assigned to a custom zone.
#                                               # Writing zone_id: null is prohibited (D-06 sparse model).
#     }
#   }
#   Empty dict = all rooms inherit the global time program.
#   A room entry only appears if it has a non-default (custom) time program.
#
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",   # "scheduled" | "force_present" | "force_absent" | "ha"
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
#
# Zones sub-schema (keyed by UUID string — D-07):
#   {
#     "<uuid>": {
#       "name": "<string>",          # display name (user-editable)
#       "mode": "<global_mode>",     # same enum as global_mode:
#                                    #   off | time_program | time_program_presences
#       "time_program": {            # same structure as global_time_program
#         "mon": [{"start": "HH:MM", "mode": "<period_mode>"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       }
#     }
#   }
#   Empty dict = no custom zones exist (all rooms belong to Default Zone).
#   Default Zone is NOT stored here — it is a virtual zone backed by
#   global_mode + global_time_program + default_zone_name (D-01, D-02, D-03).
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
    "global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "rooms": {},  # sparse: only rooms with non-default config (SCHED-05, D-11)
    "persons": {},  # sparse: only persons with non-default settings (D-11)
    # D-03: Default Zone display name (user-editable in Phase 5/6)
    "default_zone_name": "Home",
    "zones": {},  # ZONE-01: custom zones, keyed by UUID string (D-07)
    # Empty dict = no custom zones; all rooms belong to Default Zone.
    # DEFAULT_CONFIG["zones"] MUST stay {} — pitfall 2: dict.update()
    # would resurrect deleted zones if DEFAULT_CONFIG["zones"] were
    # non-empty.
}
