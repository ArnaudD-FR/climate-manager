# Phase 16: Presence & Heating Log Traces - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 16-presence-heating-log-traces
**Areas discussed:** Name format in logs, Zone state definition, Reason field
detail level, Anti-spam tracking granularity

---

## Name format in logs

| Option | Description | Selected |
|--------|-------------|----------|
| Short suffix | Strip domain: person.alice → alice | ✓ |
| Full entity ID | person.alice as-is, unambiguous | |
| Display name from config | Config-stored name (requires lookup) | |

**User's choice:** Short suffix for all (person, room, zone names)
**Notes:** Confirmed to apply the same rule consistently across all three log
event types. Strip `area_` prefix for room IDs, `zone_` prefix for zone IDs,
domain prefix for person entity IDs.

---

## Zone state definition

| Option | Description | Selected |
|--------|-------------|----------|
| Active period name | frost→normal, period changes only | |
| Zone mode | off→time_program, mode changes only | |
| Both period and mode | state=frost[time_program]→normal[time_program_presences] | ✓ |

**User's choice:** Both period and mode — with a centralized state machine
**Notes:** User specified a full state machine design pattern (not just logging).
The discussion expanded significantly:

1. Zone gets `zone.py` with `Zone`/`ZoneMode` classes and `change_mode(reason)`.
2. Person gets `person.py` with `Person`/`PersonMode` classes and
   `change_mode(reason)` / `evaluate(ts)`.
3. Room gets `room.py` as a plain class (pre-heat common to all zone modes,
   lives on Room base).
4. TRV gets `trv.py` with async `push_temperature`, `push_off`, `calibrate`.
5. Four separate module files, coordinator becomes an orchestrator.
6. User explicitly confirmed: full state machine in Phase 16 (not deferred).

---

## Reason field detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Mode name only | reason=scheduled, reason=ha | ✓ (presence) |
| Mode + resolution | reason=scheduled:present | |
| You decide | Defer to planner | |

**Presence reason:** Mode name only — `reason=scheduled`, `reason=ha`,
`reason=calendar`, `reason=force_present`, `reason=force_absent`.

| Option | Description | Selected |
|--------|-------------|----------|
| Trigger type only | reason=time_program, reason=mode_off | |
| Trigger + detail | reason=time_program:normal→22:00 | ✓ |
| You decide | Defer to planner | |

**Zone reason:** Trigger + detail — `reason=time_program:normal→22:00`,
`reason=user:time_program→off`, `reason=presence:override`.

---

## Anti-spam tracking granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Domain object state is sufficient | Zone._current_period/_current_mode, Person._last_home | ✓ |
| Explicit separate log guard | Separate _last_logged dict | |

**User's choice:** Domain object state is sufficient
**Notes:** With Zone/Person as proper classes, the state they track IS the
anti-spam guard. No additional dict needed. TRV.last_pushed already handles
the heating log anti-spam (push-on-change guard).

---

## Claude's Discretion

- Exact `ZoneMode.get_room_states(ts)` and `handle_switch(reason)` method
  signatures — confirmed general shape, exact parameter names left to planner.
- `PersonMode.is_present(ts, **ctx)` — `**ctx` contents (calendar_cache,
  start_of_local_day, etc.) left to planner.
- How `Room.calibrate_trvs` / `TRV.calibrate` integrate with existing
  calibration coordinator logic — structural migration left to planner.

## Deferred Ideas

- Multi-language support — out of scope, deferred per REQUIREMENTS.md.
- Boiler demand control — deferred to v1.4+.
- Per-zone boiler declaration — deferred to v1.4+.
- Full WS API handler migration through domain objects — current WS handlers
  still mutate config dicts; domain objects absorb state. Full unification is
  a future phase.
