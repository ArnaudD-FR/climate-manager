# SPDX-License-Identifier: MIT
"""Simple-schedule use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities) and a single pinned moment in time. The generator
(docs/use-cases/generate.py) feeds this to the real coordinator and records
the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

# --- Zone weekly programs (period mode per time-of-day) --------------------
_WEEKDAY = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:30", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_WEEKEND = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "normal"},
    {"start": "10:00", "mode": "comfort"},
    {"start": "14:00", "mode": "normal"},
    {"start": "23:00", "mode": "frost_protection"},
]


def _week(weekday, weekend):
    return {
        "mon": weekday,
        "tue": weekday,
        "wed": weekday,
        "thu": weekday,
        "fri": weekday,
        "sat": weekend,
        "sun": weekend,
    }


# Emma's presence schedule — present overnight; absent only while at work.
_EMMA_WD = [
    {"start": "00:00", "state": "present"},
    {"start": "09:00", "state": "absent"},
    {"start": "17:30", "state": "present"},
]
_EMMA_WE = [
    {"start": "00:00", "state": "present"},
]

# Two variants of the same configuration show the presence gate. In
# "Scheduled" mode presence is computed from Emma's schedule + the current
# time, so the contrast is just two moments: home in the evening (rooms follow
# the schedule) vs. at work midday (rooms set back to Reduced). The coordinator
# computes each result — the away TRV temperatures below are cosmetic only.
_AWAY_TRVS = {
    "climate.living_room_trv": {"attributes": {"current_temperature": 18.2}},
    "climate.kitchen_trv": {"attributes": {"current_temperature": 18.6}},
    "climate.bedroom_trv": {"attributes": {"current_temperature": 17.9}},
    "climate.home_office_trv": {"attributes": {"current_temperature": 18.1}},
    "person.emma": {"state": "not_home"},
}

SCENARIO = {
    "slug": "simple-schedule",
    "variants": [
        {
            "id": "present",
            "now": "2026-06-03T19:00:00+00:00",
            "caption": (
                "Wednesday 19:00 — Emma is home for the evening, so every "
                "room follows the schedule (Normal)."
            ),
        },
        {
            "id": "away",
            "now": "2026-06-03T12:00:00+00:00",
            "caption": (
                "Wednesday 12:00 — Emma is at work, so the presence gate "
                "sets every room back to Reduced."
            ),
            "states": _AWAY_TRVS,
        },
    ],
    "config": {
        "period_temperatures": {
            "frost_protection": 7,
            "reduced": 16,
            "normal": 20,
            "comfort": 22,
        },
        # Single Default Zone — presence-driven so Emma's absence gates
        # heating during work hours.
        "default_zone": {
            "name": "Home",
            "mode": "time_program_presences",
            "time_program": _week(_WEEKDAY, _WEEKEND),
        },
        "zones": {},
        "rooms": {
            "living_room": {},
            "kitchen": {},
            "bedroom": {},
            "home_office": {},
        },
        "persons": {
            "person.emma": {
                "mode": "scheduled",
                "schedule_type": "single",
                # Emma assigned to all rooms — every room gated by her
                # presence, so the zone sets back during her work hours.
                "room_ids": [
                    "bedroom",
                    "home_office",
                    "living_room",
                    "kitchen",
                ],
                "schedule": _week(_EMMA_WD, _EMMA_WE),
            },
        },
        "climate_entities": [
            "climate.living_room_trv",
            "climate.kitchen_trv",
            "climate.bedroom_trv",
            "climate.home_office_trv",
        ],
    },
    # Discovery result: area_id → climate entity_ids in that area.
    "rooms": {
        "living_room": ["climate.living_room_trv"],
        "kitchen": ["climate.kitchen_trv"],
        "bedroom": ["climate.bedroom_trv"],
        "home_office": ["climate.home_office_trv"],
    },
    # Cosmetic humidity per room (copied from old STATUS.rooms_status).
    "humidity": {
        "living_room": 46,
        "kitchen": 52,
        "bedroom": 54,
        "home_office": 49,
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.4,
                    "temperature": 20,
                },
            },
            "climate.kitchen_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Kitchen TRV",
                    "current_temperature": 21.1,
                    "temperature": 20,
                },
            },
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 19.8,
                    "temperature": 20,
                },
            },
            "climate.home_office_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Home Office TRV",
                    "current_temperature": 20.2,
                    "temperature": 20,
                },
            },
            "person.emma": {
                "state": "home",
                "attributes": {"friendly_name": "Emma"},
            },
        },
        "areas": {
            "living_room": {
                "area_id": "living_room",
                "name": "Living Room",
                "floor_id": "ground_floor",
            },
            "kitchen": {
                "area_id": "kitchen",
                "name": "Kitchen",
                "floor_id": "ground_floor",
            },
            "bedroom": {
                "area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": "first_floor",
            },
            "home_office": {
                "area_id": "home_office",
                "name": "Home Office",
                "floor_id": "first_floor",
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
