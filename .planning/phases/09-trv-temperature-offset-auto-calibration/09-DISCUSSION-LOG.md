# Phase 9: TRV Temperature Offset Auto-Calibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 09-trv-temperature-offset-auto-calibration
**Areas discussed:** Calibration cadence, Offset math, UI scope in Global Settings,
Sensor source resolution

---

## Calibration Cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Same minute cadence as eval | Calibration runs as a separate pass inside async_evaluate, every minute | ✓ |
| Separate slower interval (e.g. 15 min) | Dedicated async_track_time_interval; second cancel callback | |
| Hardcoded slow cadence via counter | Call counter skips calibration every N evals | |

**User's choice:** Same minute cadence as eval

---

| Option | Description | Selected |
|--------|-------------|----------|
| End of async_evaluate, after push | Calibration runs inline in async_evaluate after temperature push | |
| Separate private method _async_calibrate() | Called from async_evaluate; cleaner separation | ✓ |

**User's choice:** Separate private method called from async_evaluate

**Notes:** User clarified that `async_evaluate` should not own any logic —
it should only call private and explicit methods. This applies broadly to the
coordinator architecture, not just calibration.

---

## Offset Math

| Option | Description | Selected |
|--------|-------------|----------|
| delta = room_sensor_temp − TRV.current_temperature | Gap between room truth and TRV reading | ✓ |
| Something else | Freeform formula | |

**User's choice:** delta = room_sensor_temp − TRV.current_temperature

---

| Option | Description | Selected |
|--------|-------------|----------|
| new_offset = current_TRV_offset + delta (incremental) | Reads current attribute, adds delta; converges | ✓ |
| new_offset = delta (absolute, ignores current offset) | Simpler but risks over/under-correction | |
| new_offset = round(current_offset + delta, 0.5°C steps) | Rounded to TRV service step values | |

**User's choice:** new_offset = current_TRV_offset + delta (incremental)

---

| Option | Description | Selected |
|--------|-------------|----------|
| TRV state attribute temperature_offset | hass.states.get(entity_id).attributes.get('temperature_offset', 0) | ✓ |
| Track offset in integration storage | Store last applied offset; more reliable if attribute absent | |

**User's choice:** TRV state attribute temperature_offset

---

## UI Scope in Global Settings

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle only | Enabled/disabled toggle; threshold at default 0.5°C not surfaced | ✓ |
| Toggle + threshold input | Toggle + number input for threshold | |
| Toggle + threshold + interval | Toggle, threshold, and calibration interval field | |

**User's choice:** Toggle only

---

| Option | Description | Selected |
|--------|-------------|----------|
| New ha-card section: 'Calibration' | Third ha-card below Temperatures | |
| Inside the Configuration card | Below global mode selector in existing card | |
| New ha-card section: 'Options' | User-specified: general-purpose options card | ✓ |

**User's choice:** New ha-card section called "Options" (not "Calibration").
User noted there is no more Configuration card.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Native input[type=checkbox] | Consistent with HA 2026.x approach to broken ha-* elements | |
| ha-switch web component | HA toggle switch; cleaner look | ✓ |

**User's choice:** ha-switch web component
**Notes:** Despite HA 2026.x reliability concerns with ha-* components, user
specifically chose ha-switch. If it renders nothing in production, fall back
to a styled native checkbox.

---

## Sensor Source Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Manual room config only | Only rooms with explicit temperature_sensor in room config | ✓ |
| Config first, then auto-discovery fallback | Manual config + discover_room_sensors() fallback | |

**User's choice:** Manual room config only
**Notes:** Honors the word "configured" in CALIB-05. Predictable — no surprise
corrections from auto-discovered sensors the user didn't intend for calibration.

---

## Claude's Discretion

None — all four areas were decided by the user.

## Deferred Ideas

- Configurable threshold in UI (threshold only in storage, default 0.5°C)
- Configurable calibration interval (uses eval cadence for now)
- Auto-discovery sensor fallback (manual config only for now)
