# Phase 5: Zone CRUD & Evaluation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 5-Zone CRUD & Evaluation Engine
**Areas discussed:** Initial zone state, WS command set, EVAL-04 edge case, Zone presence semantics (EVAL-03)

---

## Initial Zone State

| Option | Description | Selected |
|--------|-------------|----------|
| time_program | Same as DEFAULT_GLOBAL_MODE — zone is active from creation | ✓ |
| off | Zone starts disabled; user must enable it | |
| Mirror global mode | Copies current global_mode at creation time | |

**User's choice:** time_program

---

| Option | Description | Selected |
|--------|-------------|----------|
| Copy of global_time_program | User's tuned schedule — most useful starting point | ✓ |
| _DEFAULT_DAILY_PROGRAM | Fixed factory default — predictable but ignores existing config | |

**User's choice:** Copy of global_time_program (deepcopy at creation time)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Full zone config object | Returns {zone_id, name, mode, time_program} | ✓ |
| Just zone_id | Returns {zone_id}; frontend fetches config separately | |
| Success + full config snapshot | Returns entire runtime_config | |

**User's choice:** Full zone config object — enables Phase 6 frontend to render new zone tab immediately.

---

## WS Command Set

| Option | Description | Selected |
|--------|-------------|----------|
| Separate commands per concern | create_zone, delete_zone, rename_zone, set_zone_mode, set_zone_time_program, reset_zone_time_program | ✓ |
| create + unified set_zone_config + delete | Fewer commands; set_zone_config sparse-merges like set_room_config | |
| You decide | Claude picks the structure | |

**User's choice:** Separate commands per concern — mirrors existing granular WS pattern.

---

| Option | Description | Selected |
|--------|-------------|----------|
| No reset command needed | set_zone_time_program covers any target | |
| Yes, add reset_zone_time_program | Mirrors reset_time_program for global | |
| One command with target param | reset_zone_time_program(zone_id, target: 'default'\|'global') | ✓ |

**User's choice:** One command with target param. Free-text: "The reset button should offer reset to default values or to default zone values."
**Notes:** 'default' → _DEFAULT_DAILY_PROGRAM, 'global' → copy of global_time_program.

---

## EVAL-04 Edge Case

| Option | Description | Selected |
|--------|-------------|----------|
| Frost only — zone=off wins | Zone=off overrides global presence | |
| Presence warms even in zone=off | Global presences mode overrides frost | |
| global time_program used as base | Zone mode ignored; fall back to global | |

**User's choice:** Free-text clarification: "there is no zone off, the global mode and time program from storage is related to the default zone."

**Notes:** Critical architectural clarification — `global_mode` is the Default Zone's mode, not a system-wide override. Zones are fully independent. EVAL-04 means: Default Zone rooms with presences mode get presence logic. Custom zones are not affected by global_mode.

---

| Option | Description | Selected |
|--------|-------------|----------|
| global_mode = Default Zone's mode only | EVAL-04 scoped to Default Zone rooms | ✓ |
| global_mode = system-wide meta-mode | Would override all zones | |

**User's choice:** global_mode is Default Zone's mode — EVAL-04 is not a cross-zone override.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Custom zones unaffected by global_mode=off | Each zone is independent | ✓ |
| global_mode=off is a system-wide kill switch | All rooms → frost | |

**User's choice:** Custom zones are unaffected — fully independent per-zone evaluation.

---

## Zone Presence Semantics (EVAL-03)

| Option | Description | Selected |
|--------|-------------|----------|
| All configured persons | Same list as global presence evaluation | ✓ |
| Only persons in the zone's rooms | Scoped presence per zone | |

**User's choice:** All configured persons — zone presence uses the same person list as global.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — zone time_program is the base | compute_occupied_temp uses zone.time_program | ✓ |
| No — global_time_program is always the base | Zone time_program ignored for presence computation | |

**User's choice:** Zone time_program is the base schedule for presence computation.

---

## Claude's Discretion

None — all areas had explicit user decisions.

## Deferred Ideas

None — discussion stayed within phase scope.
