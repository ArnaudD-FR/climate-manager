# Research Summary

**Project:** Climate Manager — Home Assistant Custom Integration
**Synthesized:** 2026-05-15 **Overall confidence:** MEDIUM-HIGH

---

## Executive Summary

Climate Manager is a Home Assistant custom integration that drives Tado X TRVs
(via Matter) according to weekday-based time programs, per-room schedule
overrides, and a first-class person presence model — all configured through a
built-in Lovelace panel. No existing integration covers all three dimensions
simultaneously.

The recommended implementation is a 5-layer Python backend (Storage → pure
scheduling/presence engines → coordinator control loop → WebSocket API →
Lit/TypeScript frontend), following canonical HA integration architecture.
Starting from `ludeeus/integration_blueprint` ensures HACS compatibility and CI
from day one.

The single biggest technical risk is correctness on HA restart and time-edge
events (DST, midnight crossings, TRV unavailability). Competing integrations
uniformly fail by restoring stale state rather than recomputing from current
time. Restart catch-up must be a Phase 1 concern, not a retrofit.

---

## Stack

**Python Backend** — all HA built-ins, no external PyPI deps:

- `homeassistant.helpers.storage.Store` — only correct mechanism for large
  mutable nested data
- `DataUpdateCoordinator` — integration spine; feeds all CoordinatorEntity
  subclasses
- `async_track_point_in_time` — fires exactly at next period boundary; constant
  overhead
- `async_track_state_change_event` — `async_track_state_change` removed in HA
  2025.5

**Two-call TRV control pattern (order matters, both blocking):**

1. `climate.set_hvac_mode` → `heat` (Matter `auto` mode broken on Tado X)
2. `climate.set_temperature` → target temp

**Frontend Panel:**

- Lit 3 + TypeScript 5 + Vite 5 — HA-native; `<ha-*>` components compose
  natively
- `home-assistant-js-websocket` — official HA JS library; canonical
  panel-to-backend channel
- Served from `custom_components/climate_manager/www/`, registered via
  `frontend.async_register_panel`

**Tooling:** `ludeeus/integration_blueprint` scaffold, `uv`,
`pytest-homeassistant-custom-component`, GitHub Actions (hassfest + HACS action)

---

## Table Stakes Features (v1)

- Global mode switch (Off / Time program / Time program + presence)
- Named temperature presets: Frost 7°C / Reduced 18°C / Normal 20°C / Comfort
  22°C (configurable)
- Weekday-aware time program with weekday-set grouping
- Full 24-hour coverage with implicit midnight end
- Per-room schedule override with global fallback (`time_program: null` →
  inherits global)
- Room → climate entity association (one room → one or more climate entities)
- **Correct state on HA restart (recomputed, not restored)** — #1 real-world
  competitor failure
- Full UI configuration via Lovelace panel, no YAML

## Differentiators (v1)

- Person presence via periodic schedule (first-class — no external automations
  needed)
- Person → room associations (room-level presence, not just global home/away)
- Weekday-set grouping matching real household patterns (Mon–Thu, not just
  weekday/weekend)

## Deferred to v2

- Calendar-based presence (iCal, Pronote)
- GPS / zone-based presence
- Holiday / date-range period overrides
- Predictive pre-heat

---

## Architecture

**5 layers (strict, no cross-layer dependencies):**

```
1. storage.py          — Load/save JSON via Store; schema versioning
2. scheduler.py        — Pure Python: room → temperature at time T (no HA imports)
   presence.py         — Pure Python: person → present/absent at time T (no HA imports)
3. coordinator.py      — Control loop; single evaluate_all_rooms() for atomic evaluation;
                         startup catch-up; point-in-time scheduling; listener cancellation
4. websocket.py        — CRUD API: climate_mgr/get_config, set_config, get_rooms,
                         set_room, get_persons, set_person; batch mutations only
5. frontend/           — Lit + TypeScript + Vite; 3 sections; WebSocket only
```

**Build order:**

1. Foundation → 2. Engines + tests → 3. Coordinator (hardware validate with Tado
   X) → 4. WebSocket API → 5. Frontend → 6. HA Services (optional)

Phase 3 must be hardware-validated before Phase 4 begins — a coordinator flaw
found mid-frontend forces two-layer simultaneous rework.

---

## Top Pitfalls

| #   | Pitfall                                  | Prevention                                                                           | Phase |
| --- | ---------------------------------------- | ------------------------------------------------------------------------------------ | ----- |
| C1  | No restart catch-up                      | Evaluate `dt_util.now()` in `async_added_to_hass`; push correct setpoint immediately | 1+3   |
| C2  | DST transition breaks scheduler          | Always use `dt_util.now()`, never `datetime.now()`                                   | 2     |
| C3  | TRV unavailability causes silent failure | Re-apply setpoint on `unavailable → available` state change                          | 3     |
| C4  | Manual TRV adjustment write-storm        | Never subscribe to TRV `state_changed` as re-apply trigger                           | 3     |
| M5  | Ghost listeners on unload                | Store all cancel callbacks; call all in `async_unload_entry`                         | 3     |
| M2  | Frontend JS 404                          | Register static path in `async_setup` before `async_register_panel`                  | 5     |

---

## Open Questions (resolve before/during planning)

**Product decisions (needed before Phase 2 engine implementation):**

- Presence + per-room schedule interaction: does presence gate whether the
  room's time program runs, or does it apply a hardcoded temperature? (Spec
  implies: presence gates the program; the program's temperature applies)
- Person "Automatic" mode with no schedule configured: default to present or
  absent?
- Multiple TRVs per room, partial unavailability: fail-open per entity?
  (Recommended: yes)

**Technical verification (needed before respective phase):**

- Phase 3: Prototype `async_track_point_in_time` reliability across DST on real
  HA hardware. If unreliable, fall back to `async_track_time_change`.
- Phase 5: Verify `async_register_panel` signature against current HA source;
  confirm static file serving path; decide Lit bundling strategy.
