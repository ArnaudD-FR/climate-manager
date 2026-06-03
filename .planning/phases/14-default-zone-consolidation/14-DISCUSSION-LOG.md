# Phase 14: Default Zone Consolidation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in CONTEXT.md — this log
> preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 14-default-zone-consolidation
**Areas discussed:** Frontend migration scope, WS command unification,
Storage migration strategy

---

## Frontend Migration Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full migration in Phase 14 | Update types.ts + all component refs to use config.default_zone.* | ✓ |
| Backend compat shim | Keep flat keys in responses; defer frontend migration | |

**User's choice:** Full migration in Phase 14

---

| Option | Description | Selected |
|--------|-------------|----------|
| Pass config.default_zone directly to zone-tab | Remove inline synthesis in main.ts | ✓ |
| Keep synthesis shim in main.ts | Construct zone object from nested keys explicitly | |

**User's choice:** Pass config.default_zone directly

---

**Discussion on get_status / StatusPayload:**

User raised that `get_status` was introduced before zones and `global_mode`
in the status response is a legacy artifact. Discussion explored who calls
`get_status` (only main.ts, as an initial-load fallback before the first
`subscribe_status` push) and how `rooms_status` is coordinator-push-driven.

Outcome: `get_status`/`subscribe_status` payload redesign — remove
`global_mode` + top-level `active_period`, add
`zones: Record<string, { mode, active_period }>` (nested). `rooms_status`
stays in the same payload (coordinator state, not worth splitting).
`ws_get_status` delegates to `coordinator._build_status_payload()` to
eliminate existing duplication.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep global_mode in StatusPayload | Read from config['default_zone']['mode']; zero frontend status changes | |
| Rename to default_zone_mode | Consistent naming; update 3 reader locations | |
| Nested zone objects | zones: { 'default': { mode, active_period }, ... } | ✓ |

**User's choice:** Nested zone objects

---

## WS Command Unification

| Option | Description | Selected |
|--------|-------------|----------|
| set_zone_mode accepts zone_id='default' | Remove set_global_mode; unified path | ✓ |
| Keep set_global_mode as thin alias | Backward-compatible; frontend unchanged | |

**User's choice:** Remove set_global_mode; extend set_zone_mode

---

| Option | Description | Selected |
|--------|-------------|----------|
| Fold reset_time_program into reset_zone_time_program | Remove command; extend with zone_id='default' | ✓ |
| Keep reset_time_program as thin alias | Less frontend churn | |

**User's choice:** Remove reset_time_program; extend reset_zone_time_program

---

| Option | Description | Selected |
|--------|-------------|----------|
| Keep name, update internal read | reset_room_to_global_program stays; reads default_zone.time_program | |
| Rename to reset_room_to_default_zone_program | Full consistency with new terminology | ✓ |

**User's choice:** Rename to reset_room_to_default_zone_program

---

## Storage Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot on-load: promote + write back | Migration runs once; old keys gone after first save | |
| Lazy read-time transform, never write back | Build default_zone in memory on every load; no explicit migration | ✓ |

**User's choice:** Lazy read-time transform (no explicit write-back)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Move day-fill logic inside compat shim | Single unified load-time normalization step | ✓ |
| Keep as a separate pass after the shim | Two distinct passes; easier to review in isolation | |

**User's choice:** Move inside the compat shim

---

## Claude's Discretion

None — all areas had clear user preference.

## Deferred Ideas

- `room_mode: custom` removal — Phase 15 (ARCH-02), not touched here
- Per-zone boiler declaration — deferred to v1.4+
- `get_status` command rename — payload shape changes but type string
  stays `get_status` to avoid unnecessary WS API churn
