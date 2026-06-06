# SPDX-License-Identifier: MIT
"""Shared-custody (odd/even weeks) use-case scenario.

A scenario is the *user-authored* world: the zones / rooms / persons a user
would configure, plus the surrounding Home Assistant state (TRV temperatures,
person entities, calendar events) and a single pinned moment in time. The
generator (docs/use-cases/generate.py) feeds this to the real coordinator and
records the status it computes — no hand-written status values.

See docs/use-cases/AGENT.md for the authoring guide.
"""

ZONE_ID = "zone-childroom-4d8e"

# --- Zone weekly programs (period mode per time-of-day) --------------------
_HOME_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "07:30", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "17:30", "mode": "normal"},
    {"start": "22:00", "mode": "frost_protection"},
]
_HOME_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "14:00", "mode": "normal"},
    {"start": "23:00", "mode": "frost_protection"},
]

_CHILD_WD = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "07:00", "mode": "normal"},
    {"start": "09:00", "mode": "reduced"},
    {"start": "16:00", "mode": "normal"},
    {"start": "21:00", "mode": "frost_protection"},
]
_CHILD_WE = [
    {"start": "00:00", "mode": "frost_protection"},
    {"start": "08:00", "mode": "comfort"},
    {"start": "20:30", "mode": "frost_protection"},
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


# --- Sofia's presence schedule (even/odd) ----------------------------------
_PRONOTE = {
    "entity_id": "calendar.pronote",
    "event_means": "absent",
    "gap_handling": "threshold",
    "gap_threshold_minutes": 60,
}

_CAL_DAY = [
    {"start": "00:00", "state": "calendar", "calendar_config": _PRONOTE}
]
_ALL_ABSENT = [{"start": "00:00", "state": "absent"}]

# Odd week — child here for the working week; handover OUT at Friday noon.
_ODD_FRI = [
    {"start": "00:00", "state": "calendar", "calendar_config": _PRONOTE},
    {"start": "12:00", "state": "absent"},
]
_SCHEDULE_ODD = {
    "mon": _CAL_DAY,
    "tue": _CAL_DAY,
    "wed": _CAL_DAY,
    "thu": _CAL_DAY,
    "fri": _ODD_FRI,
    "sat": _ALL_ABSENT,
    "sun": _ALL_ABSENT,
}

# Even week — handover IN at Friday noon; manual weekend schedule.
_EVEN_FRI = [
    {"start": "00:00", "state": "absent"},
    {"start": "12:00", "state": "present"},
]
_WEEKEND_MANUAL = [
    {"start": "00:00", "state": "present"},
    {"start": "14:00", "state": "absent"},
    {"start": "18:00", "state": "present"},
]
_SCHEDULE_EVEN = {
    "mon": _ALL_ABSENT,
    "tue": _ALL_ABSENT,
    "wed": _ALL_ABSENT,
    "thu": _ALL_ABSENT,
    "fri": _EVEN_FRI,
    "sat": _WEEKEND_MANUAL,
    "sun": _WEEKEND_MANUAL,
}

# Two variants on the same odd custody week (Wednesday, ISO week 23) show the
# presence gate on the Child's Room zone. Presence is driven by the Pronote
# calendar (Absent during events): at 16:30 the school day is over (last class
# ended 16:00) so the child is home and the room follows its schedule; at 10:00
# a class is in session so the child is at school and the room sets back to
# Reduced. The Home zone (living room) is a plain time program — it is the same
# in both, unaffected by presence. The away TRV temperature is cosmetic.
_AWAY = {
    "person.sofia": {"state": "not_home"},
    "climate.child_bedroom_trv": {"attributes": {"current_temperature": 17.7}},
}

SCENARIO = {
    "slug": "shared-custody-odd-even-weeks",
    "variants": [
        {
            "id": "present",
            "now": "2026-06-03T16:30:00+00:00",
            "caption": (
                "Wednesday 16:30, odd week — the school day is over, so the "
                "child is home and the Child's Room follows its schedule "
                "(Normal)."
            ),
        },
        {
            "id": "away",
            "now": "2026-06-03T10:00:00+00:00",
            "caption": (
                "Wednesday 10:00, odd week — a class is in session, so the "
                "Pronote calendar marks the child at school and the Child's "
                "Room sets back to Reduced."
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
        # Living room on ground floor — Default Zone "Home", time_program.
        "default_zone": {
            "name": "Home",
            "mode": "time_program",
            "time_program": _week(_HOME_WD, _HOME_WE),
        },
        # Child's bedroom on first floor — custom presence-driven zone.
        "zones": {
            ZONE_ID: {
                "name": "Child's Room",
                "mode": "time_program_presences",
                "time_program": _week(_CHILD_WD, _CHILD_WE),
            },
        },
        # child_bedroom → Child's Room zone; living_room → Default Zone.
        "rooms": {
            "child_bedroom": {"zone_id": ZONE_ID},
            "living_room": {},
        },
        "persons": {
            # Scheduled / even_odd with mixed calendar + manual schedule.
            # Odd week = working week here (Pronote weekdays, leaves Friday
            # noon). Even week = arrives Friday noon, manual weekend schedule.
            "person.sofia": {
                "mode": "scheduled",
                "schedule_type": "even_odd",
                "room_ids": ["child_bedroom"],
                "schedule_odd": _SCHEDULE_ODD,
                "schedule_even": _SCHEDULE_EVEN,
            },
        },
        "climate_entities": [
            "climate.child_bedroom_trv",
            "climate.living_room_trv",
        ],
    },
    # Discovery result: area_id -> climate entity_ids in that area.
    "rooms": {
        "child_bedroom": ["climate.child_bedroom_trv"],
        "living_room": ["climate.living_room_trv"],
    },
    # Cosmetic humidity per room.
    "humidity": {"child_bedroom": 55, "living_room": 47},
    # Calendar events for the pinned day. Two class blocks; the 16:00 block
    # ends at 16:00 so at 16:30 the child is home (Pronote events absent,
    # gap > 60 min threshold so no gap-fill back to absent).
    "calendars": {
        "calendar.pronote": {
            "events": [
                {
                    "start": "2026-06-03T08:00:00+00:00",
                    "end": "2026-06-03T12:00:00+00:00",
                    "summary": "Cours",
                },
                {
                    "start": "2026-06-03T13:30:00+00:00",
                    "end": "2026-06-03T16:00:00+00:00",
                    "summary": "Cours",
                },
            ],
        },
    },
    # Home Assistant world the panel renders from.
    "hass": {
        "states": {
            "climate.child_bedroom_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Child's Bedroom TRV",
                    "current_temperature": 18.8,
                    "temperature": 20,
                },
            },
            "climate.living_room_trv": {
                "state": "heat",
                "attributes": {
                    "friendly_name": "Living Room TRV",
                    "current_temperature": 20.3,
                    "temperature": 20,
                },
            },
            "person.sofia": {
                "state": "home",
                "attributes": {"friendly_name": "Sofia"},
            },
            # Pronote school-timetable calendar — drives weekday presence.
            "calendar.pronote": {
                "state": "off",
                "attributes": {"friendly_name": "Pronote — Collège"},
            },
        },
        "areas": {
            "child_bedroom": {
                "area_id": "child_bedroom",
                "name": "Child's Bedroom",
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
