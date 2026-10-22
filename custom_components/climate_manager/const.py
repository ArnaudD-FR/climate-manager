# SPDX-License-Identifier: MIT
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
# Room-only effective period while pre-heat holds the upcoming setpoint
# ahead of the next occupied time. Not a schedulable period.
PERIOD_PREHEAT = "preheat"

# Ordered enums — select options / enum sensor options and WS schema gates.
VALID_MODES: list[str] = [
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
]
VALID_PERIODS: list[str] = [
    PERIOD_FROST_PROTECTION,
    PERIOD_REDUCED,
    PERIOD_NORMAL,
    PERIOD_COMFORT,
]

# ---------------------------------------------------------------------------
# Presence mode constants (PERSON-01; Pitfall 7 — define before use in schedule.py; D-21)
# ---------------------------------------------------------------------------

PRESENCE_AUTOMATIC = "scheduled"
PRESENCE_PRESENT = "force_present"
PRESENCE_ABSENT = "force_absent"
PRESENCE_HA = "ha"
PRESENCE_CALENDAR = "calendar"

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULT_GLOBAL_MODE = MODE_TIME_PROGRAM
DEFAULT_PREHEAT_LEAD_MINUTES: int = 60

# Max seconds to wait for one TRV service call (set_temperature,
# set_hvac_mode, set_temperature_offset). A reachable-but-unresponsive valve
# must never stall the evaluation of the other rooms.
TRV_COMMAND_TIMEOUT: float = 30

# Phase 12 pre-heat constants (D-01, PREHEAT-01, D-08, D-09, GAP-01)
# preheat_enabled moved to zone scope (GAP-01):
#   - Custom zone: zones[zone_id]["preheat_enabled"] (bool, absent=False)
#   - Default Zone: top-level default_zone_preheat_enabled (bool, absent=False)
# Sparse room key (still per-room):
#   preheat_max_lead_minutes (int, absent=DEFAULT_PREHEAT_MAX_LEAD_MINUTES)
DEFAULT_PREHEAT_MAX_LEAD_MINUTES: int = 120  # D-01 / PREHEAT-01
# Min samples before the learned heating rate replaces the max lead (D-08)
PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD: int = 3
# Samples kept per room; the learned rate is their median (D-08)
PREHEAT_MAX_SAMPLES: int = 7
# °C tolerance for convergence detection (D-09)
PREHEAT_CONVERGENCE_THRESHOLD: float = 0.2
# Safety margin added to the learned lead (rate × gap × (1 + margin))
PREHEAT_LEAD_MARGIN: float = 0.1
# Shortest lead: radiator warm-up time even for a tiny gap
PREHEAT_MIN_LEAD_MINUTES: int = 10
# Smallest start gap (°C) that yields a meaningful rate sample
PREHEAT_MIN_SAMPLE_DELTA: float = 0.5
# While a pre-heat runs, the TRV gets setpoint + factor × (setpoint − room
# temperature), capped at PREHEAT_BOOST_MAX. The factor is learned per room
# (no setting), starting at DEFAULT_PREHEAT_BOOST_FACTOR.
DEFAULT_PREHEAT_BOOST_FACTOR: float = 2.0
PREHEAT_BOOST_FACTOR_MAX: float = 5.0
PREHEAT_BOOST_MAX: float = 3.0
# Boost factor learning: after each boosted run, the peak above the target over
# PREHEAT_OVERSHOOT_WINDOW_MINUTES once reached moves the factor by one
# step, within [PREHEAT_BOOST_FACTOR_MIN, PREHEAT_BOOST_FACTOR_MAX]: down
# above PREHEAT_OVERSHOOT_HIGH, up when the target came late (or never)
# with less than PREHEAT_OVERSHOOT_LOW.
PREHEAT_BOOST_FACTOR_MIN: float = 0.5
PREHEAT_BOOST_FACTOR_STEP: float = 0.5
PREHEAT_OVERSHOOT_WINDOW_MINUTES: int = 60
PREHEAT_OVERSHOOT_HIGH: float = 0.5
PREHEAT_OVERSHOOT_LOW: float = 0.2
# Highest setpoint assumed when a TRV does not report max_temp
DEFAULT_TRV_MAX_TEMP: float = 30.0

# Boiler control (sparse runtime_config["boiler"], absent = not controlled):
#   {"entity_id": "climate.*" | "switch.*" | "input_boolean.*",
#    "on_hvac_mode": "heat", "off_hvac_mode": "off",   # climate only
#    "min_on_minutes": 10, "min_off_minutes": 10}
# The boiler heats while at least one room's effective period is one of
# BOILER_HEATING_PERIODS. Do NOT add to DEFAULT_CONFIG.
BOILER_DOMAINS: tuple[str, ...] = ("climate", "switch", "input_boolean")
BOILER_HEATING_PERIODS: frozenset[str] = frozenset(
    {PERIOD_NORMAL, PERIOD_COMFORT, PERIOD_PREHEAT}
)
DEFAULT_BOILER_ON_HVAC_MODE = "heat"
DEFAULT_BOILER_OFF_HVAC_MODE = "off"
DEFAULT_BOILER_MIN_ON_MINUTES: int = 10
DEFAULT_BOILER_MIN_OFF_MINUTES: int = 10
BOILER_MAX_MIN_MINUTES: int = 60

GAP_HANDLING_EXACT = "exact"
GAP_HANDLING_DAY_SPAN = "day_span"
GAP_HANDLING_THRESHOLD = "threshold"
DEFAULT_GAP_THRESHOLD_MINUTES: int = 30

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
#       "temperature_sensor": "<entity_id>",  # optional (D-16) — string entity ID
#       "humidity_sensor": "<entity_id>",     # optional (D-16) — string entity ID
#       "zone_id": "<uuid>",                  # optional UUID — absent = Default Zone
#                                             # (D-05, D-06); null prohibited.
#       "preheat_max_lead_minutes": <int>     # optional (GAP-01); per-room only.
#                                             # preheat_enabled removed (GAP-01):
#                                             # moved to zone scope — see Zones
#                                             # sub-schema and
#                                             # default_zone_preheat_enabled below.
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
#       "schedule": {                # used when schedule_type == "single" (default)
#         "mon": [{"start": "HH:MM", "state": "present"|"absent"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       },
#       "schedule_type": "single" | "even_odd",  # SCHED-01/03; absent = "single"
#       "schedule_even": { ... },   # SCHED-03; same structure as schedule;
#                                   # used during even ISO weeks (parity == 0)
#       "schedule_odd":  { ... },   # SCHED-03; same structure as schedule;
#                                   # used during odd ISO weeks (parity == 1)
#       "calendar_config": {        # CAL-01; sparse — absent = not using
#                                   # Calendar mode (D-08, D-09). Shape:
#                                   #   {"entity_id": "calendar.*",
#                                   #    "event_means": "absent"|"present"}
#                                   # default event_means = "absent".
#                                   # Do NOT add to DEFAULT_CONFIG (D-09).
#       },
#       "preheat_lead_minutes": 60, # CAL-04; sparse — absent = default 60.
#                                   # Per-person, range 0–480 (D-10, D-11).
#                                   # Do NOT add to DEFAULT_CONFIG (D-09).
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
#       "time_program": {            # same structure as default_zone.time_program
#         "mon": [{"start": "HH:MM", "mode": "<period_mode>"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       },
#       "preheat_enabled": <bool>    # optional (GAP-01); absent = False.
#                                    # True enables predictive pre-heat for
#                                    # all rooms assigned to this zone.
#     }
#   }
#   Empty dict = no custom zones exist (all rooms belong to Default Zone).
#   Default Zone is stored under the `default_zone` key (D-01, Phase 14):
#   a single first-class ZoneConfig mirroring the custom zone shape.
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    # Phase 14 (D-01): Default Zone as first-class ZoneConfig.
    # The four old flat keys (global_mode, global_time_program,
    # default_zone_name, default_zone_preheat_enabled) are absent.
    "default_zone": {
        "name": "Home",
        "mode": DEFAULT_GLOBAL_MODE,
        "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
        "preheat_enabled": False,
    },
    "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
    "rooms": {},  # sparse: only rooms with non-default config (SCHED-05, D-11)
    "persons": {},  # sparse: only persons with non-default settings (D-11)
    "zones": {},  # ZONE-01: custom zones, keyed by UUID string (D-07)
    # Empty dict = no custom zones; all rooms belong to Default Zone.
    # DEFAULT_CONFIG["zones"] MUST stay {} — pitfall 2: dict.update()
    # would resurrect deleted zones if DEFAULT_CONFIG["zones"] were
    # non-empty.
    "calibration_enabled": False,  # CALIB-01: global on/off toggle
    "calibration_threshold": 0.5,  # CALIB-04: jitter guard in degrees C
    # D-02: sparse default — absent key = no mapping, no migration needed.
    "matter_mappings": {},
}
