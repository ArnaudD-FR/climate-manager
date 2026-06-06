# SPDX-License-Identifier: MIT
"""Business-calendar use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities, calendar events) and a single pinned moment in time. The
generator (docs/use-cases/generate.py) feeds this to the real coordinator and
records the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

OFFICE_ZONE_ID = "zone-office-7f3a"

# --- Zone weekly programs (period mode per time-of-day) --------------------
_HOME_WEEKDAY = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:00", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_HOME_WEEKEND = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "23:00", "mode": "frost_protection"},
]
_OFFICE_WEEKDAY = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "18:00", "mode": "frost_protection"},
]
_OFFICE_WEEKEND = [
    {"start": "00:00", "mode": "frost_protection"},
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


SCENARIO = {
    "slug": "business-calendar",
    # Wednesday 10:30 — a normal working morning with no meeting active, so
    # Noah counts as home and his rooms heat. (June 1 2026 is a Monday.)
    "now": "2026-06-03T10:30:00+00:00",
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
            "time_program": _week(_HOME_WEEKDAY, _HOME_WEEKEND),
        },
        "zones": {
            OFFICE_ZONE_ID: {
                "name": "Office",
                "mode": "time_program_presences",
                "time_program": _week(_OFFICE_WEEKDAY, _OFFICE_WEEKEND),
            },
        },
        "rooms": {
            "home_office": {"zone_id": OFFICE_ZONE_ID},
            "bedroom": {},
            "living_room": {},
        },
        "persons": {
            "person.noah": {
                "mode": "calendar",
                "room_ids": ["home_office", "bedroom", "living_room"],
                "calendar_config": {
                    "entity_id": "calendar.work_meetings",
                    "event_means": "absent",
                    "gap_handling": "day_span",
                },
                "wakeup_advance_minutes": 30,
            },
        },
        "climate_entities": [
            "climate.home_office_trv",
            "climate.bedroom_trv",
            "climate.living_room_trv",
        ],
    },
    # Discovery result: area_id -> climate entity_ids in that area.
    "rooms": {
        "home_office": ["climate.home_office_trv"],
        "bedroom": ["climate.bedroom_trv"],
        "living_room": ["climate.living_room_trv"],
    },
    # Cosmetic humidity per room (the engine has no humidity sensor here).
    "humidity": {"home_office": 43, "bedroom": 55, "living_room": 47},
    # Calendar events for the pinned day. A single afternoon meeting, so the
    # morning (10:30) is free — Noah is home.
    "calendars": {
        "calendar.work_meetings": {
            "events": [
                {
                    "start": "2026-06-03T14:00:00+00:00",
                    "end": "2026-06-03T15:00:00+00:00",
                    "summary": "Team sync",
                },
            ],
        },
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.home_office_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Home Office TRV",
                    "current_temperature": 21.8,
                    "temperature": 22,
                },
            },
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 19.6,
                    "temperature": 20,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.4,
                    "temperature": 20,
                },
            },
            "person.noah": {
                "state": "home",
                "attributes": {"friendly_name": "Noah"},
            },
            "calendar.work_meetings": {
                "state": "off",
                "attributes": {"friendly_name": "Work Meetings"},
            },
        },
        "areas": {
            "home_office": {
                "area_id": "home_office",
                "name": "Home Office",
                "floor_id": "first_floor",
            },
            "bedroom": {
                "area_id": "bedroom",
                "name": "Bedroom",
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
