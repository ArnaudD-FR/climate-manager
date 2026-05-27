---
created: 2026-05-27T00:00:00.000Z
title: Adaptive pre-heat with dynamic room inertia learning
area: general
files: []
---

## Problem

Rooms only start heating when a comfort or normal period begins, so it takes time to
reach the target temperature. Users want rooms to already be at the right temperature
at the start of a period — requiring the system to start heating ahead of time.

The required lead time (pre-heat duration) varies per room and depends on:
- The temperature delta between current temperature and target setpoint
- The room's thermal inertia (how fast it heats up per degree delta)
- The boiler flow temperature, which is set by a heat curve function of outdoor
  temperature — a colder day means higher flow temp and faster room heat-up, so
  inertia cannot be treated as a fixed per-room constant

Room inertia is not known upfront and must be learned empirically. Because the
effective heating power changes with outdoor temperature (via the boiler heat curve),
the learned factor must be normalised to a reference flow temperature, and the
pre-heat lead time must be re-computed at runtime using the current outdoor temperature.

This requires Climate Manager to detect and read the boiler entity from HA.

## Solution

**Algorithm — adaptive pre-heat with inertia learning:**

1. **Initial guess**: start with a fixed lead time (e.g. 60 min) before the next
   normal/comfort period begins.

2. **Observation**: record the actual time the room took to reach the target
   temperature after heating started (T_actual).

3. **Inertia factor computation**: derive a per-room `inertia_factor` normalised to a
   reference flow temperature (e.g. 60°C):
   - `raw_rate = ΔT_room / T_actual`  (°C/min of room heat-up)
   - `flow_temp` = boiler supply temperature read from HA at heating start
   - `normalised_inertia = raw_rate × (T_flow_ref / flow_temp)`
   - Stored as `inertia_factor` (normalised °C/min at T_flow_ref)

4. **Iteration**: on the next cycle, compute lead time using current conditions:
   - `flow_temp_now` = boiler supply temp predicted at pre-heat start time
     (estimated from heat curve: `f(T_outdoor)` — can be read from boiler entity
     or approximated from a configurable heat curve table)
   - `effective_rate = inertia_factor × (flow_temp_now / T_flow_ref)`
   - `lead_time = (ΔT / effective_rate) × safety_margin`
   - Converges after 3–5 heating cycles across comparable outdoor conditions

5. **Convergence**: once inertia_factor stabilises (< 10% change between consecutive
   cycles), treat it as learned and reduce the safety margin toward 1.0.

6. **Pre-heat cap** (`preheat_max_duration`, default 120 min, configurable per room):
   - The computed `lead_time` is clamped to `preheat_max_duration` before use.
   - If the room never reaches the target within the pre-heat window (e.g. poorly
     insulated room, very cold day, undersized radiator), the observation is marked
     as `did_not_converge = true` and excluded from inertia learning — the sample
     must not corrupt the model by implying an infinite inertia.
   - A warning is surfaced in the panel (e.g. "Room X could not reach target in time")
     so the user knows the cap was hit and can raise it or investigate the root cause.

7. **Mode compatibility**:
   - Pre-heat works with `time_program_presences`: the presence schedule is known in
     advance (persons have fixed weekly or even/odd schedules), so the system can
     compute the next "person becomes present" transition and pre-heat toward it —
     identical logic to pre-heating toward a comfort/normal period start.
   - The only truly incompatible case is live/reactive presence detection (e.g. HA
     device tracker firing when someone actually arrives home with no schedule) — in
     that case there is no future transition time to target. For rooms whose heating
     depends on such a source, `preheat_enabled` is ignored and the room shows the
     "Pre-heat disabled — presence cannot be scheduled." warning.

8. **Other edge cases**:
   - Room already at target: no pre-heat needed
   - Inertia not yet learned: use conservative default (60 min), capped by `preheat_max_duration`
   - Pre-heat window extends into a frost/reduced period: start from the boundary

**Standard abacus reference**: ISO 13790 / EN 12831 simplified thermal model is the
industry standard for residential heating lead-time estimation. The `inertia_factor`
above is an empirical simplification of the time constant `τ = C/UA` from that model.

**UI — pre-heat status display:**
- When a room is actively pre-heating, its period status label in the time-bar and
  room card shows **"Pre-heating (→ XX.X°C)"** instead of the current mode label,
  so the user can see at a glance that early heating is in progress and what the
  target is.
- This requires the coordinator to expose a `preheat_active: bool` and
  `preheat_target: float` field in the per-room status payload (WebSocket
  `get_status` / `subscribe_status`).

**UI — pre-heat disabled warning:**
- When `preheat_enabled` is true for a room but pre-heat is automatically inactive
  because the presence source is live/reactive (no fixed schedule to target), the
  room card shows: **"Pre-heat disabled — presence cannot be scheduled."**
- This tells the user why their pre-heat setting has no effect, and implicitly
  nudges them to switch to a scheduled presence source if they want pre-heat to work..

**Boiler detection (prerequisite):**
- Climate Manager needs a new optional `boiler_entity` config field pointing to a
  HA `climate` or `sensor` entity that exposes the boiler's supply (flow) temperature
- If `boiler_entity` is set, the integration reads `current_temperature` (flow temp)
  from it at each schedule evaluation; if unset, pre-heat falls back to a
  user-configured fixed flow temperature assumption
- Outdoor temperature: read from a configurable `outdoor_temp_entity` (sensor) — used
  both for heat curve estimation and for grouping inertia samples by weather conditions
- This boiler/outdoor detection is a standalone sub-feature that benefits other parts
  of the system beyond pre-heat (e.g. could inform boiler efficiency metrics later)

**Data to persist per room:**
- `preheat_enabled: bool`
- `preheat_max_duration: int` (minutes, default 120)
- `inertia_factor: float | null` (null = not yet learned; normalised to T_flow_ref)
- `inertia_samples: list[{delta_t_room, flow_temp, outdoor_temp, lead_time, actual_time, did_not_converge, timestamp}]` (last N samples)

**Global config additions:**
- `boiler_entity: str | null`
- `outdoor_temp_entity: str | null`
- `preheat_flow_temp_ref: float` (default 60.0 °C — normalisation reference)

**Minor version bump** — additive feature, no breaking changes to existing config.
