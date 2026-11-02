# SPDX-License-Identifier: MIT
"""Family holiday use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities) and a single pinned moment in time. The generator
(docs/use-cases/generate.py) feeds this to the real coordinator and records
the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

# --- Zone weekly programs (period mode per time-of-day) --------------------
_HOME_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "08:30", "mode": "reduced"},
    {"start": "17:30", "mode": "normal"},
    {"start": "22:30", "mode": "frost_protection"},
]
_HOME_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "normal"},
    {"start": "22:30", "mode": "frost_protection"},
]
# Bathroom: warm for the morning and the evening, whoever is home.
_BATH_WD = [
    {"start": "00:00", "mode": "reduced"},
    {"start": "06:30", "mode": "comfort"},
    {"start": "08:30", "mode": "reduced"},
    {"start": "18:30", "mode": "comfort"},
    {"start": "21:30", "mode": "reduced"},
]
_BATH_WE = [
    {"start": "00:00", "mode": "reduced"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "10:00", "mode": "reduced"},
    {"start": "18:30", "mode": "comfort"},
    {"start": "21:30", "mode": "reduced"},
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


# --- Presence schedules ----------------------------------------------------
# Both parents work office hours; home (and asleep = present) otherwise.
_WORK_WD = [
    {"start": "00:00", "state": "present"},
    {"start": "08:30", "state": "absent"},
    {"start": "17:30", "state": "present"},
]
_ALL_DAY = [{"start": "00:00", "state": "present"}]

_BATHROOM_ZONE = "zone-bathroom-5f2c"

# One household absence: the whole family is skiing from Saturday 14 to
# Sunday 22 February, back at 17:00. No person is selected, so the period
# covers everyone and also drives the Time program bathroom zone.
_HOLIDAY = {
    "id": "winter-holiday",
    "kind": "absent",
    "start": "2026-02-14T09:00",
    "end": "2026-02-22T17:00",
}

# Two moments of the same configuration. "away": Wednesday evening of the
# holiday, when the schedules would normally have everyone home — the
# absence wins, every room (bathroom included) stays at Reduced. "present"
# (configuration captures): Sunday 15:30, 90 minutes before the return, the
# rooms with a lead time are pre-heating so the house is warm at 17:00.
# Nobody is home in either moment; the TRV temperatures are cosmetic.
_AWAY_TRVS = {
    "climate.living_room_trv": {"attributes": {"current_temperature": 16.2}},
    "climate.bedroom_trv": {"attributes": {"current_temperature": 16.0}},
    "climate.kids_room_trv": {"attributes": {"current_temperature": 16.1}},
    "climate.bathroom_trv": {"attributes": {"current_temperature": 16.4}},
}

SCENARIO = {
    "slug": "family-holiday",
    "variants": [
        {
            "id": "present",
            "now": "2026-02-22T15:30:00+00:00",
            "caption": (
                "Sunday 15:30 — the family is due back at 17:00, so the "
                "rooms with a lead time are already pre-heating."
            ),
        },
        {
            "id": "away",
            "now": "2026-02-18T19:00:00+00:00",
            "caption": (
                "Wednesday 19:00, mid-holiday — the schedules would have "
                "everyone home, but the absence holds every room at Reduced."
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
        "default_zone": {
            "name": "Home",
            "mode": "time_program_presences",
            "time_program": _week(_HOME_WD, _HOME_WE),
            "preheat_enabled": True,
        },
        "zones": {
            _BATHROOM_ZONE: {
                "name": "Bathroom",
                "mode": "time_program",
                "time_program": _week(_BATH_WD, _BATH_WE),
                "preheat_enabled": True,
            },
        },
        "rooms": {
            "living_room": {"preheat_max_lead_minutes": 120},
            "bedroom": {"preheat_max_lead_minutes": 120},
            "kids_room": {"preheat_max_lead_minutes": 120},
            "bathroom": {
                "zone_id": _BATHROOM_ZONE,
                "preheat_max_lead_minutes": 120,
            },
        },
        "persons": {
            "person.claire": {
                "mode": "scheduled",
                "schedule_type": "single",
                "room_ids": ["living_room", "bedroom"],
                "schedule": _week(_WORK_WD, _ALL_DAY),
            },
            "person.hugo": {
                "mode": "scheduled",
                "schedule_type": "single",
                "room_ids": ["living_room", "kids_room"],
                "schedule": _week(_WORK_WD, _ALL_DAY),
            },
        },
        "presence_periods": [_HOLIDAY],
        "climate_entities": [
            "climate.living_room_trv",
            "climate.bedroom_trv",
            "climate.kids_room_trv",
            "climate.bathroom_trv",
        ],
    },
    # Discovery result: area_id -> climate entity_ids in that area.
    "rooms": {
        "living_room": ["climate.living_room_trv"],
        "bedroom": ["climate.bedroom_trv"],
        "kids_room": ["climate.kids_room_trv"],
        "bathroom": ["climate.bathroom_trv"],
    },
    # Cosmetic humidity per room.
    "humidity": {
        "living_room": 45,
        "bedroom": 50,
        "kids_room": 48,
        "bathroom": 58,
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 16.3,
                    "temperature": 20,
                },
            },
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 16.1,
                    "temperature": 20,
                },
            },
            "climate.kids_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Kids Room TRV",
                    "current_temperature": 16.2,
                    "temperature": 20,
                },
            },
            "climate.bathroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bathroom TRV",
                    "current_temperature": 16.5,
                    "temperature": 22,
                },
            },
            # Away skiing: HA home tracking would say so too, but both
            # follow their schedule — the absence period is what holds.
            "person.claire": {
                "state": "not_home",
                "attributes": {"friendly_name": "Claire"},
            },
            "person.hugo": {
                "state": "not_home",
                "attributes": {"friendly_name": "Hugo"},
            },
        },
        "areas": {
            "living_room": {
                "area_id": "living_room",
                "name": "Living Room",
                "floor_id": "ground_floor",
            },
            "bedroom": {
                "area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": "first_floor",
            },
            "kids_room": {
                "area_id": "kids_room",
                "name": "Kids Room",
                "floor_id": "first_floor",
            },
            "bathroom": {
                "area_id": "bathroom",
                "name": "Bathroom",
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
