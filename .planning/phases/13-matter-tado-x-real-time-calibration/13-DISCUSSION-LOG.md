# Phase 13: Matter→Tado X Real-Time Calibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 13-matter-tado-x-real-time-calibration
**Areas discussed:** Mapping config, Event filtering, Listener lifecycle,
Frontend scope, Mapping algorithm (follow-up), Control flow, Zone entity
fallback, Calibration source, Config schema shape, Control path algorithm
(follow-up clarification)

---

## Mapping Config

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect | If room has Tado X devices + calibration_enabled, register listener automatically | ✓ (initially) |
| Per-room toggle | New sparse key; user enables per room | |
| Global toggle | Single switch for all Tado X rooms | |

**User's choice:** Auto-detect (initial answer), then evolved through
follow-up questions into an explicit per-room mapping config.

**Notes:** After further discussion, the "auto-detect" simplification was
replaced by an explicit `matter_mappings` config at the root level. The user
clarified that: (1) each physical TRV needs individual pairing, (2) the mapping
should be user-controlled, not auto-inferred, and (3) the mapping changes how
TRV control works (not just calibration).

---

## Event Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Filter to current_temperature changes | Skip non-calibration state changes | ✓ |
| Fire on any state_changed | Simpler handler; threshold gate handles noise | |

**User's choice:** Filter to `current_temperature` attribute changes only.

**Notes:** Matter climate entities fire `state_changed` on setpoint changes and
hvac_action changes too — filtering prevents spurious calibration passes.

---

## Listener Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Per-room dict in coordinator | `_matter_cal_listeners: dict[str, list]` keyed by area_id | |
| Append to cancel_registry_listeners | Handles unload but not individual removal | |

**User's choice:** Per-entity dict in coordinator (evolved to entity_id key
during refinement, mirrors `_ha_tracker_listeners`).

**Notes:** User also clarified listener scope: mapped rooms → Matter listeners
only; unmapped rooms → both Matter and tado_x listeners (unmapped entities
are independent).

---

## Frontend Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Backend-only | MCALIB-01/02 are pure backend requirements | ✓ (initially) |
| Add room card indicator | Subtle "real-time calibration active" label | |

**User's choice:** Initially backend-only, but during the control path and
mapping config discussion it became clear that a per-TRV pairing UI in the
room card is required to configure the mappings.

**Notes:** Phase 13 includes frontend work for the mapping configuration UI.

---

## Mapping Algorithm (Follow-up)

**User's clarification:** The algorithm must handle multiple TRVs per room.
One tado_x zone entity maps to N Matter climate entities (one per physical TRV).
With mappings, Matter entities replace the tado_x entity for setpoint control.
Matter `current_temperature` already includes the applied offset.

---

## Control Path (Follow-up)

**User's algorithm:**
1. Loop over all area climate entities
2. tado_x entity → look for mapping; if found, mark mapped Matter entities;
   if not found, mark tado_x entity
3. matter entity → check if in any mapping value; if not, mark as independent
4. Set all marked entities

**Notes:** tado_x replaced entirely (no fallback) when mapping exists.
Unmapped Matter entities treated as independent.

---

## Config Schema Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Area-keyed dict of pairs | `{ area_id: [{matter_entity_id, tado_device_id}] }` | |
| Flat matter→device dict | `{ matter_entity_id: tado_device_id }` | |
| Tado-keyed list | `{ tado_device_id: [matter_entity_ids] }` (user suggestion) | |
| Tado entity_id keyed | `{ tado_entity_id: [matter_entity_ids] }` | ✓ |

**User's choice:** User initially suggested `{ tado_device_id: [...] }`.
After clarifying that `tado_x` creates one zone entity per room (not per device),
user selected tado_x entity_id as the key — direct O(1) lookup in control loop.

---

## Calibration Source (Follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Matter entity current_temperature | Reflects applied offset; most accurate | ✓ |
| Keep tado_x entity current_temperature | Unchanged; potentially inconsistent | |

**User's choice:** Matter entity's `current_temperature` for delta calculation.

---

## Claude's Discretion

- `matter_entity_set` frozenset built once per evaluate cycle for O(1) matter
  entity membership checks — implementation detail
- `_async_refresh_matter_listeners()` cancel-all-then-reregister approach —
  safe given HA event loop serialisation
- Room card section heading ("Matter pairing" vs "Real-time calibration") —
  planner's choice

---

## Deferred Ideas

- Fallback to tado_x entity when Matter entity is unavailable — robustness
  improvement for a future phase
- Reverse mapping display in Matter entity card — out of scope
- Bulk auto-pair by shared HA device — future UX improvement
