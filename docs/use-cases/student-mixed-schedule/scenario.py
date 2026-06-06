# SPDX-License-Identifier: MIT
"""Student-mixed-schedule use-case scenario.

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
    {"start": "07:00", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:00", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_WEEKEND = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:30", "mode": "normal"},
    {"start": "10:00", "mode": "comfort"},
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


# Lena's presence schedule — different class hours each weekday.
# Present overnight; absent only during class hours.
_LENA_MON = [
    {"start": "00:00", "state": "present"},
    {"start": "08:00", "state": "absent"},
    {"start": "16:00", "state": "present"},
]
_LENA_TUE = [
    {"start": "00:00", "state": "present"},
    {"start": "10:00", "state": "absent"},
    {"start": "13:00", "state": "present"},
]
_LENA_WED = [
    {"start": "00:00", "state": "present"},
    {"start": "08:00", "state": "absent"},
    {"start": "18:00", "state": "present"},
]
_LENA_THU = [
    {"start": "00:00", "state": "present"},
    {"start": "09:00", "state": "absent"},
    {"start": "12:00", "state": "present"},
]
_LENA_FRI = [
    {"start": "00:00", "state": "present"},
    {"start": "08:00", "state": "absent"},
    {"start": "14:00", "state": "present"},
]
_LENA_WE = [
    {"start": "00:00", "state": "present"},
]

SCENARIO = {
    "slug": "student-mixed-schedule",
    # Wednesday 19:00 — Lena is home after a heavy class day (classes ended
    # at 18:00), so all her rooms heat to Normal.
    "now": "2026-06-03T19:00:00+00:00",
    "config": {
        "period_temperatures": {
            "frost_protection": 7,
            "reduced": 16,
            "normal": 20,
            "comfort": 22,
        },
        # Single Default Zone — presence-driven so class-hour absences gate
        # heating per day.
        "default_zone": {
            "name": "Home",
            "mode": "time_program_presences",
            "time_program": _week(_WEEKDAY, _WEEKEND),
        },
        "zones": {},
        "rooms": {
            "bedroom": {},
            "study": {},
            "living_room": {},
        },
        "persons": {
            "person.lena": {
                "mode": "scheduled",
                "schedule_type": "single",
                # Lena assigned to all rooms — every room is gated by her
                # class-hour absences.
                "room_ids": ["bedroom", "study", "living_room"],
                "schedule": {
                    "mon": _LENA_MON,
                    "tue": _LENA_TUE,
                    "wed": _LENA_WED,
                    "thu": _LENA_THU,
                    "fri": _LENA_FRI,
                    "sat": _LENA_WE,
                    "sun": _LENA_WE,
                },
            },
        },
        "climate_entities": [
            "climate.bedroom_trv",
            "climate.study_trv",
            "climate.living_room_trv",
        ],
    },
    # Discovery result: area_id → climate entity_ids in that area.
    "rooms": {
        "bedroom": ["climate.bedroom_trv"],
        "study": ["climate.study_trv"],
        "living_room": ["climate.living_room_trv"],
    },
    # Cosmetic humidity per room (copied from old STATUS.rooms_status).
    "humidity": {
        "bedroom": 56,
        "study": 48,
        "living_room": 45,
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 20.1,
                    "temperature": 20,
                },
            },
            "climate.study_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Study TRV",
                    "current_temperature": 19.5,
                    "temperature": 20,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.7,
                    "temperature": 20,
                },
            },
            "person.lena": {
                "state": "home",
                "attributes": {"friendly_name": "Lena"},
            },
        },
        "areas": {
            "bedroom": {
                "area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": "first_floor",
            },
            "study": {
                "area_id": "study",
                "name": "Study",
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
