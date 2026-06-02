# Phase 12: Predictive Pre-heat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 12-predictive-pre-heat
**Areas discussed:** Per-room vs per-person lead time, Next-transition
computation, Inertia learning model, Pre-heat status in the panel

---

## Per-room vs per-person lead time

| Option | Description | Selected |
|--------|-------------|----------|
| Per-room (migrate) | preheat_enabled + preheat_max_lead_minutes on room config; thermal inertia is a room property; drop per-person preheat_lead_minutes | |
| Both: per-person lead, per-room enable | Keep preheat_lead_minutes per-person; add preheat_enabled per-room | |
| Per-room only, with global default | Each room has config; global default until room sets its own | |

**User's choice:** Pre-heat is per-room. When a room is scheduled to be heated, this is the pre-heat duration. The existing `preheat_lead_minutes` is badly named and should be renamed as **wake-up advance** (a distinct per-person concept: start heating before a calendar-mode person returns home).

**Follow-up — room schema:**

| Option | Description | Selected |
|--------|-------------|----------|
| preheat_enabled + preheat_max_lead_minutes | Toggle + cap; learned lead time stored separately | ✓ |
| preheat_enabled only | Just a toggle; no cap | |
| preheat_enabled + fixed lead (no learning yet) | Ship fixed config; defer inertia | |

**Notes:** Two concepts clearly separated — (1) per-person `wakeup_advance_minutes` (Phase 11 concept, renamed); (2) per-room adaptive pre-heat (Phase 12, new).

---

## Next-transition computation

| Option | Description | Selected |
|--------|-------------|----------|
| New next_occupied_at() helper in schedule.py | Pure function; coordinator calls it per person; takes earliest | ✓ |
| Inline in coordinator per presence mode | No new helper | |
| Pre-compute at evaluate time, cache per person | One-time per cycle | |

**Follow-up — HA mode:**

| Option | Description | Selected |
|--------|-------------|----------|
| Suppress pre-heat, show warning | next_occupied_at() returns None; "Pre-heat disabled" shown | ✓ |
| Use last known pattern as heuristic | Complex, unreliable | |
| Disable pre-heat toggle for HA-only rooms | UI greyed out | |

**Follow-up — multi-person rooms:**

| Option | Description | Selected |
|--------|-------------|----------|
| Earliest next_occupied_at across all persons | Any person coming home triggers pre-heat | ✓ |
| Only when ALL persons present | Much less common | |
| Configurable per-room: any vs all | Adds schema complexity | |

**Notes:** No additional questions — all three sub-questions resolved clearly.

---

## Inertia learning model

| Option | Description | Selected |
|--------|-------------|----------|
| Time from TRV call to target reached | Simple, directly observable | ✓ |
| Time from cold start corrected for ambient | More accurate, complex | |
| Rolling average of evaluate cycles | Same as option 1 phrased differently | |

**Follow-up — sample storage:**

| Option | Description | Selected |
|--------|-------------|----------|
| New key in Store alongside room config | preheat_samples as separate Store key | |
| Inline on each room config dict | Simpler access, mixes config and state | |
| Separate .storage file (climate_manager_preheat.json) | Clean separation | ✓ |

**Follow-up — combining samples:**

| Option | Description | Selected |
|--------|-------------|----------|
| Simple average of last 5 valid samples | Easy to reason about; capped at max | ✓ |
| EWMA | Better seasonal adaptation; needs alpha param | |
| Median of last 5 | Robust to outliers | |

**Notes:** Clean separation of learning data from user config via separate Store file.

---

## Pre-heat status in the panel

| Option | Description | Selected |
|--------|-------------|----------|
| New attribute on room state in WS response | Extend existing get_state / state_updated | ✓ |
| Separate push event: preheat_changed | New WS event type | |
| HA entity attribute on sensor entity | Couples panel to entity names | |

**Follow-up — pre-heat config location in room card:**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in room card, below TRV list | Same pattern as Phase 9 calibration | ✓ |
| Collapsible "Advanced" section | More compact | |
| Dedicated pre-heat panel section | Breaks per-room card pattern | |

**Notes:** Three WS fields: `preheat_active` (bool), `preheat_target` (float), `preheat_suppressed` (bool). Status text is subtle — small text line, not a warning badge.

---

## Claude's Discretion

- Minimum samples before learning kicks in: 3 (hardcoded, not configurable)
- Sample timestamp format: ISO 8601 UTC strings
- Convergence detection tolerance: current_temp >= target - 0.2°C
- In-progress tracking: `_preheat_in_progress` dict on coordinator instance

## Deferred Ideas

- EWMA / ambient-corrected learning models — too complex for Phase 12
- Sample pruning by age — timestamps stored but pruning out of scope
- Pre-heat for force_present / force_absent — no deterministic next transition
- Boiler demand control integration — separate feature, own phase
