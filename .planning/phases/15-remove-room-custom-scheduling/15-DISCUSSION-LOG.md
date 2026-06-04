# Phase 15: Remove Room-Level Mode Override - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in CONTEXT.md — this log preserves the
> alternatives considered.

**Date:** 2026-06-04
**Phase:** 15-remove-room-custom-scheduling
**Areas discussed:** Frost rooms on upgrade, Custom rooms + orphaned
time_program, Room card after picker removal

---

## Frost Rooms on Upgrade

| Option | Description | Selected |
|--------|-------------|----------|
| Strip silently | Remove room_mode from the record. Room follows its zone. User re-assigns to a MODE_OFF zone if needed. | ✓ |
| Log a WARNING per room | Strip but emit a one-time WARNING pointing user to create a MODE_OFF zone. | |
| Auto-create a MODE_OFF zone | Create a dedicated "Frost — <room name>" zone in MODE_OFF, assign the room. | |

**User's choice:** Strip silently
**Notes:** Consistent with the general direction — no automation, no log noise.
User takes responsibility for reconfiguring if needed.

---

## Custom Rooms + Orphaned time_program

| Option | Description | Selected |
|--------|-------------|----------|
| Strip both fields silently | Remove room_mode and time_program from the record. Room follows its zone. No log. | ✓ |
| Log an INFO per room | Strip both fields but log at INFO that the custom schedule was discarded. | |

**User's choice:** Strip both fields silently
**Notes:** Same silent treatment as frost_protection. No log emitted.
Consistent decision across all room_mode values.

---

## Room Card After Picker Removal

| Option | Description | Selected |
|--------|-------------|----------|
| Zone picker only — nothing else | Remove mode select and inline time-bar entirely. Zone assignment is the only scheduling control. | (base) |
| Add a read-only zone schedule preview | Show the zone's current active period inline on the room card. | |

**User's choice:** Zone picker only (with clarification)
**Notes:** User clarified via free text: the room mode badge in the card header
is removed, but the active period status (e.g., "Normal — 20°C") and associated
zone name remain. No replacement for the mode badge.

---

## Claude's Discretion

- `set_room_config` schema cleanup: whether to explicitly reject `room_mode`
  keys or silently ignore — Claude to decide (chose explicit removal from schema)
- Test cleanup strategy: delete vs rewrite — Claude to decide (chose delete
  for tests whose sole purpose was room_mode validation)

## Deferred Ideas

None — discussion stayed within phase scope.
