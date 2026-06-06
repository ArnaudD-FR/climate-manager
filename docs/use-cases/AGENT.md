# Building use-case docs

This folder holds persona-driven showcases of Climate Manager. Each use case is
a folder with a `README.md`, a `screenshots/` set (Overview, Rooms, Persons),
and a generated `scenario.json`. This guide explains how they are built so new
use cases stay correct and coherent.

## Core principle — never hand-write status

A use case authors **only what a real user configures** (zones, rooms, persons)
plus the surrounding Home Assistant world (TRV temperatures, `person.*` states,
calendar events) and a **single pinned moment in time**. The **real
coordinator** then computes the resulting state (who is present, each room's and
zone's active period, pre-heat). We never hand-write present/absent, active
periods, or pre-heat flags — that is exactly how the screenshots drifted out of
sync before. If a value looks wrong, fix the **config or the pinned time**, not
the status.

## Pipeline

```text
<slug>/scenario.py      →  make use-case-data   →  <slug>/scenario.json
   (user config +          (real coordinator        (config + computed
    world + now)            at pinned time)           status + world)
                                                          │
                                                          ▼
_harness.html?scenario=<slug>/scenario.json  +  screenshot.js (clock pinned)
                                                          │
                                                          ▼
                                              <slug>/screenshots/*.png
```

- **`<slug>/scenario.py`** — a `SCENARIO` dict (see schema below), co-located in
  the use-case folder. The only file you author per use case besides the README.
- **`generate.py`** (`make use-case-data`) — runs on the host using the HA test
  harness. For each scenario it sets the integration's runtime config, seeds the
  HA world, pins the clock, runs the **real** `coordinator.async_evaluate()`,
  and writes `<slug>/scenario.json` from `coordinator._build_status_payload()`.
  Display-only fields (room display names, humidity) are injected from the
  scenario.
- **`_harness.html`** — one generic harness for all use cases. It reads
  `?scenario=<path>` and renders the panel from that JSON. There is no
  per-folder harness.
- **`docs/screenshot.js`** — when `SCENARIO_JSON` is set it pins the browser
  clock **and timezone to UTC** at `scenario.now`, so the panel's live
  computations (zone active period, even/odd week parity, calendar "now") match
  the coordinator status in the same file. This also makes screenshots fully
  reproducible (no wall-clock drift).
- **`<slug>/Makefile`** — copies the business-calendar one verbatim, changing
  only `SLUG`. It passes `OUTPUT_DIR`, the shared `HARNESS_PATH` with
  `?scenario=`, and `SCENARIO_JSON`.

`make screenshots` runs the standard panel-tab set, then `use-case-data`, then
captures every use case.

## `SCENARIO` schema

```python
SCENARIO = {
    "slug": "<folder-name>",
    "now": "2026-06-03T10:30:00+00:00",   # UTC; pick a moment that shows the case
    "config": { ... },        # exactly the get_config payload a user would have:
                              #   period_temperatures, default_zone, zones,
                              #   rooms, persons, climate_entities
    "rooms": { area_id: [climate_entity_ids] },   # discovery result (area→TRVs)
    "humidity": { area_id: 55 },                   # cosmetic only
    "calendars": { "calendar.x": {"events": [ {start, end, summary} ]} },
    "hass": {                  # the HA world the panel renders from
        "states": { entity_id: {"state": str, "attributes": {...}} },
        "areas":  { area_id: {"area_id", "name", "floor_id"} },
        "floors": { floor_id: {"floor_id", "name", "level"} },
    },
}
```

Times are **UTC**. Schedule `"HH:MM"` values are evaluated in UTC, so pick `now`
in UTC and reason about the schedules in UTC.

## How heating actually works (get this right in the config)

- A **zone** has one **mode** shared by all its rooms: **Off**, **Time
  program**, or **Time program & presences**.
- **Time program**: rooms heat to the scheduled period regardless of who is
  assigned — no person needed.
- **Time program & presences**: a room follows the schedule **only when at least
  one assigned person is present**; otherwise it is set back to **Reduced**. A
  room in a presences zone with **no assigned person never heats** — so every
  heating room in a presences zone needs ≥1 person in its room associations.
- Presence **does not boost** temperature — it only gates whether the zone's
  schedule applies (with gap-fill between Normal/Comfort periods). When a person
  is present, **all** rooms they are associated with follow the schedule.
- **Absent means physically away.** Someone asleep at home overnight is
  **present**; only mark a person away for the hours they are actually out.
- **Pre-heat**: a zone with pre-heat enabled starts its rooms early (up to each
  room's max lead time) so they reach target by the next warmer period / first
  event of the day. Only rooms with an assigned schedule/calendar person are
  pre-heated.
- **Wake-up advance** (Calendar mode): presence begins N minutes before the
  day's **first** calendar event — not an evening-return mechanism.

## Presence modes (panel labels)

`Scheduled` · `HA home tracking` · `Calendar` · `Force Present` ·
`Force Absent`. There is no "ha" mode in user-facing text — it is **HA home
tracking**.

## README terminology — frontend only

READMEs must use the panel's user-facing labels, never backend config keys or
stored values. Do not write `time_program_presences`, `room_ids`, `zone_id`,
`event_means`, `gap_handling`, `wakeup_advance_minutes`, `preheat_enabled`,
`'ha'`, `frost_protection`, raw `calendar.*` ids, etc. Use instead:

| Concept         | Panel label                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------- |
| zone modes      | Off / Time program / Time program & presences                                                     |
| periods         | Frost protection / Reduced / Normal / Comfort                                                     |
| presence modes  | Scheduled / HA home tracking / Calendar / Force Present / Force Absent                            |
| schedule kind   | Single week / Even / Odd weeks                                                                    |
| person→rooms    | Room associations                                                                                 |
| calendar entity | refer to it by its friendly name (Calendar source)                                                |
| event meaning   | Absent during events / Present during events                                                      |
| gap handling    | Return home between events / Absent all day (first to last event) / Return home in long gaps only |
| wake-up lead    | Wake-up advance                                                                                   |
| pre-heat        | Pre-heat / Max lead time / Pre-heating → XX.X°C                                                   |

Each README is a conceptual showcase: persona intro, a Household layout table
(Room | Zone | Floor | Heats when), a presence/schedule section, a "Rooms driven
by …" section, and a Screenshots section embedding `overview.png`, `rooms.png`,
`persons.png` with one annotated sentence each. 2-space indent, wrap at 80
columns.

## Adding a new use case

1. Create `<slug>/scenario.py` with a `SCENARIO` dict. Choose `now` to best show
   the case (e.g. a working morning, a winter evening, an odd custody week).
2. Create `<slug>/Makefile` (copy business-calendar's, change `SLUG`) and
   `<slug>/README.md`.
3. Run `make use-case-data` then `make -C docs/use-cases/<slug> screenshots` (or
   just `make screenshots` for everything).
4. **Open the screenshots and check coherence** — zone badges must match room
   periods, present persons must match warmed rooms. If something is off, fix
   the config or `now`, never the JSON.
5. Add the use case to the root `README.md` "Use cases" table.
6. `make lint`.

## Anti-patterns (these caused real bugs)

- Hand-writing `status` / `rooms_status` values → drift and incoherence.
- Assuming local time = the ISO you wrote without forcing UTC → off-by-hours
  periods (the HA test harness defaults to a non-UTC timezone).
- A room with no assigned person in a presences zone (it silently never heats).
- Marking someone absent overnight.
- Backend terminology in the README.
