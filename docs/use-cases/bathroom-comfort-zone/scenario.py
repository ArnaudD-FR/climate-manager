# SPDX-License-Identifier: MIT
"""Bathroom-comfort-zone use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities, calendar events) and a single pinned moment in time. The
generator (docs/use-cases/generate.py) feeds this to the real coordinator and
records the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

BATH_ZONE = "zone-bathrooms-2a7f"

# --- Zone weekly programs (period mode per time-of-day) --------------------
_HOME_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "08:30", "mode": "reduced"},
    {"start": "17:30", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_HOME_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "10:00", "mode": "normal"},
    {"start": "23:00", "mode": "frost_protection"},
]

# Bathrooms: comfort at wake-up, reduced weekday / normal weekend during
# the day, comfort again from 19:00.
_BATH_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "comfort"},
    {"start": "08:30", "mode": "reduced"},
    {"start": "19:00", "mode": "comfort"},
    {"start": "22:00", "mode": "frost_protection"},
]
_BATH_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "10:00", "mode": "normal"},
    {"start": "19:00", "mode": "comfort"},
    {"start": "23:00", "mode": "frost_protection"},
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


# --- Alex's presence schedule ----------------------------------------------
_ALEX_WD = [
    {"start": "00:00", "state": "present"},
    {"start": "08:30", "state": "absent"},
    {"start": "18:00", "state": "present"},
]
_ALEX_WE = [
    {"start": "00:00", "state": "present"},
]

# Two variants of the same configuration. The key contrast is that the two
# zones respond differently to presence. The Home zone is "Time program &
# presences" — gated by Alex. The Bathrooms zone is plain "Time program" — it
# follows its own comfort schedule no matter who is home, with nobody assigned.
# present (20:00): Alex home → Home Normal, Bathrooms Comfort (from 19:00).
# away (12:00): Alex at work → Home Reduced (gated), Bathrooms still driven
# purely by its own schedule (Reduced midday) — the same it would show with or
# without anyone assigned. The away TRV temperatures are cosmetic.
_AWAY = {
    "person.alex": {"state": "not_home"},
    "climate.bedroom_trv": {"attributes": {"current_temperature": 18.1}},
    "climate.living_room_trv": {"attributes": {"current_temperature": 18.5}},
}

SCENARIO = {
    "slug": "bathroom-comfort-zone",
    "variants": [
        {
            "id": "present",
            "now": "2026-06-03T20:00:00+00:00",
            "caption": (
                "Wednesday 20:00 — Alex is home, so the Home zone is at "
                "Normal; the Bathrooms zone is at Comfort on its own schedule "
                "(comfort from 19:00)."
            ),
        },
        {
            "id": "away",
            "now": "2026-06-03T12:00:00+00:00",
            "caption": (
                "Wednesday 12:00 — Alex is at work, so the Home zone sets back "
                "to Reduced; the Bathrooms zone keeps following its own "
                "schedule, unaffected by presence."
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
        # Default Zone "Home": presence-driven — Alex must be present for
        # the living areas to heat to their scheduled period.
        "default_zone": {
            "name": "Home",
            "mode": "time_program_presences",
            "time_program": _week(_HOME_WD, _HOME_WE),
        },
        # Custom "Bathrooms" zone — schedule-only, no person needed. The
        # bathrooms heat to comfort on their own program regardless of who
        # is home.
        "zones": {
            BATH_ZONE: {
                "name": "Bathrooms",
                "mode": "time_program",
                "time_program": _week(_BATH_WD, _BATH_WE),
            },
        },
        # Both bathrooms join the Bathrooms zone (time_program — no person
        # needed); living areas stay Default Zone (presences — Alex assigned).
        "rooms": {
            "main_bathroom": {"zone_id": BATH_ZONE},
            "ensuite": {"zone_id": BATH_ZONE},
            "living_room": {},
            "bedroom": {},
        },
        "persons": {
            "person.alex": {
                "mode": "scheduled",
                "schedule_type": "single",
                # Alex assigned only to Home-zone rooms; bathrooms need no
                # person because their zone is time_program.
                "room_ids": ["bedroom", "living_room"],
                "schedule": _week(_ALEX_WD, _ALEX_WE),
            },
        },
        "climate_entities": [
            "climate.main_bathroom_trv",
            "climate.ensuite_trv",
            "climate.living_room_trv",
            "climate.bedroom_trv",
        ],
    },
    # Discovery result: area_id -> climate entity_ids in that area.
    "rooms": {
        "main_bathroom": ["climate.main_bathroom_trv"],
        "ensuite": ["climate.ensuite_trv"],
        "living_room": ["climate.living_room_trv"],
        "bedroom": ["climate.bedroom_trv"],
    },
    # Cosmetic humidity per room.
    "humidity": {
        "main_bathroom": 60,
        "ensuite": 62,
        "living_room": 47,
        "bedroom": 50,
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.main_bathroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Main Bathroom TRV",
                    "current_temperature": 22.4,
                    "temperature": 22,
                },
            },
            "climate.ensuite_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Ensuite TRV",
                    "current_temperature": 22.1,
                    "temperature": 22,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.2,
                    "temperature": 20,
                },
            },
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 19.4,
                    "temperature": 20,
                },
            },
            "person.alex": {
                "state": "home",
                "attributes": {"friendly_name": "Alex"},
            },
        },
        "areas": {
            "main_bathroom": {
                "area_id": "main_bathroom",
                "name": "Main Bathroom",
                "floor_id": "first_floor",
            },
            "ensuite": {
                "area_id": "ensuite",
                "name": "Ensuite",
                "floor_id": "first_floor",
            },
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
