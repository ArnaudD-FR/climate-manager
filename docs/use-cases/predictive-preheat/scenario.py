# SPDX-License-Identifier: MIT
"""Predictive pre-heat use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities, calendar events) and a single pinned moment in time. The
generator (docs/use-cases/generate.py) feeds this to the real coordinator and
records the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

# --- Zone weekly programs (period mode per time-of-day) --------------------
_WEEKDAY = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:00", "mode": "normal"},
    {"start": "22:30", "mode": "frost_protection"},
]
_WEEKEND = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "22:30", "mode": "frost_protection"},
]


def _week(wd, we):
    return {
        "mon": wd,
        "tue": wd,
        "wed": wd,
        "thu": wd,
        "fri": wd,
        "sat": we,
        "sun": we,
    }


# --- Maya's presence schedule ----------------------------------------------
# Present overnight (asleep = present), absent 08:30–17:30 weekdays.
_MAYA_WD = [
    {"start": "00:00", "state": "present"},
    {"start": "08:30", "state": "absent"},
    {"start": "17:30", "state": "present"},
]
_MAYA_WE = [
    {"start": "00:00", "state": "present"},
]

# Two variants of the same configuration. The "present" star moment is 05:50,
# BEFORE the 06:30 wake-up step: Maya is home asleep (present overnight), so the
# zone pre-heat is already warming every room toward the morning Normal target.
# The "away" moment is midday, when Maya is out and the presence gate sets the
# rooms back to Reduced — no pre-heat runs for an empty house. The away TRV
# temperatures are cosmetic.
_AWAY = {
    "person.maya": {"state": "not_home"},
    "climate.bedroom_trv": {"attributes": {"current_temperature": 18.0}},
    "climate.bathroom_trv": {"attributes": {"current_temperature": 17.4}},
    "climate.living_room_trv": {"attributes": {"current_temperature": 18.2}},
}

SCENARIO = {
    "slug": "predictive-preheat",
    "variants": [
        {
            "id": "present",
            "now": "2026-06-03T05:50:00+00:00",
            "caption": (
                "Wednesday 05:50 — Maya is home asleep, 40 minutes before the "
                "06:30 Normal step, so pre-heat is already warming every room "
                "toward 20.0°C."
            ),
        },
        {
            "id": "away",
            "now": "2026-06-03T12:00:00+00:00",
            "caption": (
                "Wednesday 12:00 — Maya is out, so the presence gate holds "
                "every room at Reduced and no pre-heat runs."
            ),
            "states": _AWAY,
        },
    ],
    "config": {
        "period_temperatures": {
            "frost_protection": 7,
            "reduced": 16,
            "normal": 20,
            "comfort": 22,
        },
        # Default Zone with pre-heat enabled — rooms start warming early
        # ahead of the next warmer period when Maya is present overnight.
        "default_zone": {
            "name": "Home",
            "mode": "time_program_presences",
            "time_program": _week(_WEEKDAY, _WEEKEND),
            "preheat_enabled": True,
        },
        "zones": {},
        # Per-room max lead time the coordinator may use to reach target.
        # bathroom has a longer lead (tiles hold heat); living_room has none.
        "rooms": {
            "bedroom": {"preheat_max_lead_minutes": 60},
            "bathroom": {"preheat_max_lead_minutes": 90},
            "living_room": {},
        },
        "persons": {
            "person.maya": {
                "mode": "scheduled",
                "schedule_type": "single",
                # Maya assigned to all three rooms — all are in a presences
                # zone so each room must have an assigned person to heat.
                "room_ids": ["bedroom", "bathroom", "living_room"],
                "schedule": _week(_MAYA_WD, _MAYA_WE),
            },
        },
        "climate_entities": [
            "climate.bedroom_trv",
            "climate.bathroom_trv",
            "climate.living_room_trv",
        ],
    },
    # Discovery result: area_id -> climate entity_ids in that area.
    "rooms": {
        "bedroom": ["climate.bedroom_trv"],
        "bathroom": ["climate.bathroom_trv"],
        "living_room": ["climate.living_room_trv"],
    },
    # Cosmetic humidity per room.
    "humidity": {"bedroom": 52, "bathroom": 60, "living_room": 48},
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    # Below Normal target (20°C) — pre-heat is actively
                    # pushing toward it ahead of the 06:30 step.
                    "current_temperature": 17.5,
                    "temperature": 20,
                },
            },
            "climate.bathroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bathroom TRV",
                    # Below Normal target (20°C) — pre-heat active.
                    "current_temperature": 16.5,
                    "temperature": 20,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    # No max lead time so it waits for the period change.
                    "current_temperature": 15.8,
                    "temperature": 16,
                },
            },
            "person.maya": {
                "state": "home",
                "attributes": {"friendly_name": "Maya"},
            },
        },
        "areas": {
            "bedroom": {
                "area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": "first_floor",
            },
            "bathroom": {
                "area_id": "bathroom",
                "name": "Bathroom",
                "floor_id": "first_floor",
            },
            "living_room": {
                "area_id": "living_room",
                "name": "Living Room",
                "floor_id": "ground_floor",
            },
        },
        "floors": {
            "ground_floor": {
                "floor_id": "ground_floor",
                "name": "Ground Floor",
                "level": 0,
            },
            "first_floor": {
                "floor_id": "first_floor",
                "name": "First Floor",
                "level": 1,
            },
        },
    },
}
