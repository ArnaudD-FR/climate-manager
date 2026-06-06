# SPDX-License-Identifier: MIT
"""Rotating-shift-worker use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities) and a single pinned moment in time. The generator
(docs/use-cases/generate.py) feeds this to the real coordinator and records
the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

ZONE_ID = "zone-upstairs-9b2c"

# --- Zone weekly programs (period mode per time-of-day) --------------------
_DOWNSTAIRS_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "07:00", "mode": "normal"},
    {"start": "09:30", "mode": "reduced"},
    {"start": "18:00", "mode": "normal"},
    {"start": "22:30", "mode": "frost_protection"},
]
_DOWNSTAIRS_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:30", "mode": "normal"},
    {"start": "11:00", "mode": "comfort"},
    {"start": "14:00", "mode": "normal"},
    {"start": "23:00", "mode": "frost_protection"},
]

_UPSTAIRS_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "06:30", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:00", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_UPSTAIRS_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "normal"},
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


SCENARIO = {
    "slug": "rotating-shift-worker",
    # Wednesday 14:00 — Marc is home (HA home tracking confirms presence),
    # so all rooms in both zones heat to their current scheduled period.
    # Downstairs zone at 14:00 on a weekday is in Reduced (09:30–18:00),
    # Upstairs zone at 14:00 is in Reduced (09:00–17:00) — both rooms set
    # back. The coordinator computes the correct active periods.
    "now": "2026-06-03T14:00:00+00:00",
    "config": {
        "period_temperatures": {
            "frost_protection": 7,
            "reduced": 16,
            "normal": 20,
            "comfort": 22,
        },
        # Ground floor is the Default Zone — presence-driven (Downstairs).
        "default_zone": {
            "name": "Downstairs",
            "mode": "time_program_presences",
            "time_program": _week(_DOWNSTAIRS_WD, _DOWNSTAIRS_WE),
        },
        # First floor is a custom presence-driven zone (Upstairs).
        "zones": {
            ZONE_ID: {
                "name": "Upstairs",
                "mode": "time_program_presences",
                "time_program": _week(_UPSTAIRS_WD, _UPSTAIRS_WE),
            },
        },
        # bedroom is on the first floor → Upstairs zone.
        # living_room and kitchen are ground floor → Default (Downstairs).
        "rooms": {
            "bedroom": {"zone_id": ZONE_ID},
            "living_room": {},
            "kitchen": {},
        },
        "persons": {
            # HA home tracking mode — no schedule arrays.
            # Marc is assigned to all rooms so every room gates on his
            # live presence as reported by HA.
            "person.marc": {
                "mode": "ha",
                "room_ids": ["bedroom", "living_room", "kitchen"],
            },
        },
        "climate_entities": [
            "climate.bedroom_trv",
            "climate.living_room_trv",
            "climate.kitchen_trv",
        ],
    },
    # Discovery result: area_id → climate entity_ids in that area.
    "rooms": {
        "bedroom": ["climate.bedroom_trv"],
        "living_room": ["climate.living_room_trv"],
        "kitchen": ["climate.kitchen_trv"],
    },
    # Cosmetic humidity per room (copied from old STATUS.rooms_status).
    "humidity": {
        "bedroom": 54,
        "living_room": 46,
        "kitchen": 43,
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Bedroom TRV",
                    "current_temperature": 19.2,
                    "temperature": 20,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.5,
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
            # device_trackers non-empty → clean "HA home tracking" badge.
            "person.marc": {
                "state": "home",
                "attributes": {
                    "friendly_name": "Marc",
                    "device_trackers": [
                        "device_tracker.marc_phone",
                    ],
                },
            },
            "device_tracker.marc_phone": {
                "state": "home",
                "attributes": {"friendly_name": "Marc's Phone"},
            },
        },
        "areas": {
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
            "kitchen": {
                "area_id": "kitchen",
                "name": "Kitchen",
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
