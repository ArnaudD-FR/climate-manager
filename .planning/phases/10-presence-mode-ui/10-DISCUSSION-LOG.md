# Phase 10: Presence Mode UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 10-presence-mode-ui
**Areas discussed:** Hide mechanism, Stuck-mode edge case

---

## Hide Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend only | PersonsTab computes boolean from hass.states and passes prop to PersonCard. No backend changes needed. | ✓ |
| Backend flag in status payload | websocket.py injects has_device_tracker per person into get_status/subscribe_status. Cleaner for PersonCard, but requires backend + TypeScript type changes. | |

**User's choice:** Frontend only
**Notes:** PersonCard gets a new `hasDeviceTrackers: boolean` prop computed by
PersonsTab from `hass.states[personId]?.attributes?.device_trackers`. Keeps the
change entirely in the frontend; no backend deployment required.

---

## Stuck-Mode Edge Case

| Option | Description | Selected |
|--------|-------------|----------|
| Show inline warning | Render a small warning below the select: 'Live tracking requires a device tracker in HA.' The select still shows the value but the user is informed and can switch. | ✓ |
| Auto-reset to Scheduled on render | When PersonCard detects mode='ha' + hasDeviceTrackers=false, immediately call setPersonConfig({mode:'scheduled'}). Silent migration. | |
| Silent — just hide the option | Don't add the option to the select. Browser picks first visible option visually but underlying value stays 'ha'. | |

**User's choice:** Show inline warning
**Notes:** Warning text: "Live tracking requires a device tracker linked to this
person in HA." Displayed as inline text using the existing `.schedule-hint` CSS
class, not a toast or modal. No automatic WS call fired on render.

---

## Claude's Discretion

None — all decisions were made by the user.

## Deferred Ideas

- Backend `has_device_tracker` flag: reviewed as an alternative to the frontend
  approach; deferred as unnecessary complexity for this phase.
- Auto-migration of persons stuck on "ha" mode: decided against — surprising
  behavior to fire a WS call silently on render.
