# Phase 3: WebSocket API & Frontend Panel - Discussion Log (Session 2)

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in CONTEXT.md — this log preserves the
> alternatives considered.

**Date:** 2026-05-21 **Phase:** 03-websocket-api-frontend-panel **Areas
discussed:** Backend-computed status fields, Period badge colors & HA CSS, HA
component policy for 2026.x

**Session intent:** Add architectural constraints — HA component usage policy
and frontend/backend logic boundary — captured as D-23 through D-30 in
CONTEXT.md.

---

## Backend-computed status fields

| Option                               | Description                                                           | Selected |
| ------------------------------------ | --------------------------------------------------------------------- | -------- |
| Backend sends `present_person_count` | Add int field per room to `rooms_status`; no array intersection in TS | ✓        |
| Frontend `includes()` check is fine  | Simple lookup, not business logic; keep in frontend                   |          |

**User's choice:** Backend sends `present_person_count`

| Option                                   | Description                                                 | Selected |
| ---------------------------------------- | ----------------------------------------------------------- | -------- |
| Backend sorts rooms and persons          | Coordinator/websocket send pre-sorted arrays                |          |
| Frontend sort is presentation, not logic | Room/person ordering is a display concern; keep in frontend | ✓        |

**User's choice:** Frontend sort is acceptable for display ordering

| Option                               | Description                                         | Selected |
| ------------------------------------ | --------------------------------------------------- | -------- |
| Backend provides climate entity list | `get_config` includes `climate_entities: list[str]` | ✓        |
| Frontend hass.states filter is fine  | Domain filter is HA-idiomatic panel behavior        |          |

**User's choice:** Backend provides climate entity list

| Option                            | Description                                                                | Selected |
| --------------------------------- | -------------------------------------------------------------------------- | -------- |
| Keep picker filtering in frontend | Removing already-assigned items is UI state management, not business logic | ✓        |
| Backend sends pre-filtered lists  | Separate "available" lists per context                                     |          |

**User's choice:** Frontend picker filtering is acceptable

---

## Period badge colors & HA CSS

| Option                           | Description                                                            | Selected      |
| -------------------------------- | ---------------------------------------------------------------------- | ------------- |
| Custom hex values (keep current) | Period colors are product-specific; HA semantic vars don't map cleanly | ✓ (once only) |
| Map to HA semantic vars          | --success-color, --warning-color, etc. — theme-adaptive                |               |

**User's choice:** Custom hex values but defined once in `types.ts` (no inline
hex literals)

| Option                  | Description                                                       | Selected |
| ----------------------- | ----------------------------------------------------------------- | -------- |
| Always use HA CSS vars  | Audit and replace all hardcoded colors/sizes for dark mode compat | ✓        |
| Only where already done | No audit needed beyond current state                              |          |

**User's choice:** Always use HA CSS variables for non-period-badge styling

| Option                       | Description                                              | Selected |
| ---------------------------- | -------------------------------------------------------- | -------- |
| CSS :host vars per component | Define color vars at :host level in each component       |          |
| Shared types.ts const object | Export `PERIOD_COLORS` / `PRESENCE_COLORS` from types.ts | ✓        |
| CSS module / global.css      | :root vars in shared CSS file                            |          |

**User's choice:** Shared const object in `frontend/src/types.ts`

---

## HA component policy for 2026.x

| Option                             | Description                                               | Selected |
| ---------------------------------- | --------------------------------------------------------- | -------- |
| Assume working until proven broken | Default to ha-\* components; replace when rendering fails | ✓        |
| Only use confirmed-working ones    | Strict allowlist: ha-card, ha-icon, hui-thermostat-card   |          |

**User's choice:** Assume working until proven broken

| Option                | Description                                             | Selected |
| --------------------- | ------------------------------------------------------- | -------- |
| Try ha-dialog first   | Standard HA component; handles keyboard/focus-trap/a11y | ✓        |
| Native positioned div | Simpler, no HA version risk                             |          |

**User's choice:** Try ha-dialog first for popup overlays

| Option                       | Description                                         | Selected |
| ---------------------------- | --------------------------------------------------- | -------- |
| Lock native replacements now | Fixed patterns for ha-select, ha-textfield, ha-tabs |          |
| Leave flexible               | Claude's discretion per plan                        | ✓        |

**User's choice:** Specific replacement patterns at Claude's discretion per plan
(but broken components documented in CONTEXT.md D-29)

---

## Claude's Discretion

- Specific native HTML replacements for broken HA components (within the policy
  of D-29)
- Whether `climate_entities` goes in `get_config` or a new
  `get_climate_entities` command
- Exact computation location in coordinator for `present_person_count`

## Deferred Ideas

None — discussion stayed within phase scope.
