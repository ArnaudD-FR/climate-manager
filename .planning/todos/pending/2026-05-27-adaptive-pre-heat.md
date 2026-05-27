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

Room inertia is not known upfront and must be learned empirically over several cycles.

## Solution

**Algorithm — adaptive pre-heat with inertia learning:**

1. **Initial guess**: start with a fixed lead time (e.g. 60 min) before the next
   normal/comfort period begins.

2. **Observation**: record the actual time the room took to reach the target
   temperature after heating started (T_actual).

3. **Inertia factor computation**: derive a per-room `inertia_factor` (min/°C) using
   a standard thermal model:
   - `inertia_factor = T_actual / ΔT`  where `ΔT = target - start_temp`
   - This is the "degrees per minute" rate, inverted to minutes-per-degree

4. **Iteration**: on the next cycle, compute lead time as:
   - `lead_time = inertia_factor × ΔT × safety_margin` (safety_margin ≈ 1.1)
   - Converges after 3–5 heating cycles; early cycles over- or under-shoot

5. **Convergence**: once inertia_factor stabilises (< 10% change between consecutive
   cycles), treat it as learned and reduce the safety margin toward 1.0.

6. **Edge cases**:
   - Room already at target: no pre-heat needed
   - Inertia not yet learned: use conservative default (60 min)
   - Pre-heat window extends into a frost/reduced period: start from the boundary
   - Per-room opt-in: pre-heat is disabled by default, enabled per room in config

**Standard abacus reference**: ISO 13790 / EN 12831 simplified thermal model is the
industry standard for residential heating lead-time estimation. The `inertia_factor`
above is an empirical simplification of the time constant `τ = C/UA` from that model.

**Data to persist per room:**
- `preheat_enabled: bool`
- `inertia_factor: float | null` (null = not yet learned)
- `inertia_samples: list[{delta_t, lead_time, actual_time, timestamp}]` (last N samples)

**Minor version bump** — additive feature, no breaking changes to existing config.
