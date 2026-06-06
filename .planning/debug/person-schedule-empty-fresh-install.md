---
slug: person-schedule-empty-fresh-install
status: resolved
trigger: fresh HACS install — person schedule is empty when it should be pre-populated
goal: find_and_fix
created: 2026-06-06
resolved: 2026-06-06
---

# Debug: Person Schedule Empty on Fresh Install

## Symptom

On a fresh HACS install (no prior `.storage` data), every person's schedule
is empty. The presence time-bar renders blank. The default schedule that
should pre-populate the bar is never written.

## Evidence

### E-01 — Default config has empty `persons` dict (const.py:223)

```python
DEFAULT_CONFIG: dict = {
    ...
    "persons": {},  # sparse: only persons with non-default settings (D-11)
    ...
}
```

On a fresh install `ClimateManagerStore.async_load()` returns
`copy.deepcopy(DEFAULT_CONFIG)` (storage.py:99-100). The `persons` key is
an empty dict — no person entries, no schedules.

### E-02 — Default schedule seed is gated on mode _change_ (person-card.ts)

```typescript
const hasSchedule =
  !!this.config?.schedule &&
  Object.values(this.config.schedule).some((day) => day.length > 0);

if (newMode === PRESENCE_MODE_SCHEDULED && !hasSchedule) {
  await this.ws.setPersonConfig(this.personId, {
    mode: newMode,
    schedule: DEFAULT_SCHEDULE,
  });
}
```

`DEFAULT_SCHEDULE` is only written when the user explicitly selects
"Scheduled" from the mode dropdown and the schedule is empty.

### E-03 — Fresh install: person config is absent, not "scheduled"

A new person has NO entry in `runtime_config["persons"]`. The panel reads:
```typescript
const currentMode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
```
So the UI shows "Scheduled" as the selected mode — but the person entry was
never written to storage. When the mode dropdown shows "Scheduled" without
the user having touched it, `_onModeChange` never fires, and
`DEFAULT_SCHEDULE` is never seeded.

### E-04 — Config flow writes nothing (config_flow.py)

The config flow creates the entry with empty data. `async_setup_entry` then
calls `store.async_load()` which returns `DEFAULT_CONFIG` with
`persons: {}`. No per-person defaults are seeded anywhere in the Python side.

### E-05 — No backend seeding path exists

There is no code that iterates discovered persons and writes a default
schedule entry for persons not yet in `runtime_config["persons"]`.

## Root Cause

The default presence schedule for a person only exists in the **frontend**
(`DEFAULT_SCHEDULE` constant in `person-card.ts`). It is seeded into storage
only when the user **changes** the presence mode selector to "Scheduled". On
a fresh install, every person starts with no config entry at all; the UI
derives `mode = "scheduled"` from the absent-key fallback, so the mode
selector appears pre-set and `_onModeChange` is never triggered. The seed
code is therefore dead on first render.

**Root cause: the `DEFAULT_SCHEDULE` seed path in `_onModeChange` is
conditioned on a user-driven mode _change_. It never fires when a person is
already (implicitly) in Scheduled mode via the absent-key fallback, which is
the state every person is in on a fresh install.**

## Fix Applied

`frontend/src/components/person-card.ts` — three changes:

1. Added `private _scheduleSeeded = false` instance flag (prevents repeated
   seeding across re-renders).

2. Added `_seedScheduleIfNeeded()` async method that:
   - Returns immediately if `_scheduleSeeded` is true (already seeded)
   - Returns immediately if `ws`, `personId`, or `panel` are not yet set
   - Returns immediately if effective mode is not "scheduled"
   - Returns immediately if the schedule already has content
   - Sets `_scheduleSeeded = true` before the async call, resets on error
   - Calls `ws.setPersonConfig(personId, { schedule: DEFAULT_SCHEDULE })`
   - Calls `panel.reloadConfig()` to pull the seeded data back

3. In `updated()`, added `if (changedProperties.has("config")) { void
   this._seedScheduleIfNeeded(); }` so the seed fires automatically when
   the config property first arrives from the panel (fresh install path).

The existing `_onModeChange` seed path (D-22) is preserved for the switching
case (user switches from non-scheduled to scheduled mode).

`panel.js` rebuilt successfully via `make build`.

## Resolution

- root_cause: DEFAULT_SCHEDULE seed code only fires on user-driven mode
  change; fresh-install persons are implicitly "scheduled" via absent-key
  fallback, so the change event never fires and the schedule stays empty.
- fix: added automatic seed in `updated()` lifecycle — fires once per
  component instance when config is received and schedule is absent/empty
  while mode is "scheduled".
