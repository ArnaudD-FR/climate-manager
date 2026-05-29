---
phase: quick-260526-plq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - custom_components/climate_manager/coordinator.py
  - tests/test_coordinator.py
  - frontend/src/components/room-card.ts
  - frontend/src/components/person-card.ts
  - custom_components/climate_manager/www/panel.js
autonomous: true
requirements:
  - QUICK-260526-plq

must_haves:
  truths:
    - "When MODE_OFF dispatches to an off-capable TRV, the coordinator first
      issues set_temperature(frost_protection) and then issues set_hvac_mode=off
      in that order."
    - "The 'off' anti-flap sentinel still skips subsequent off cycles for the
      same entity (no regression of quick task 260526-ffr)."
    - "Non-off-capable TRVs in MODE_OFF continue to receive only the
      frost-protection temperature (unchanged)."
    - "Room card expanded body shows sections in order: Mode selector, custom
      time program + reset (when custom), Persons, then Climate entities at the
      bottom under a 'Climate entities' section label."
    - "Person card expanded body shows sections in order: Presence mode
      selector, Presence schedule (when scheduled), Associated rooms."
    - "frontend build (npm run build) regenerates
      custom_components/climate_manager/www/panel.js with 0 errors."
  artifacts:
    - path: custom_components/climate_manager/coordinator.py
      provides:
        "_push_off_safely(entity_id, frost_temp) — frost temp pushed before
        hvac=off"
    - path: tests/test_coordinator.py
      provides:
        "Updated MODE_OFF off-capable test asserting both set_temperature(frost)
        and set_hvac_mode=off are called"
    - path: frontend/src/components/room-card.ts
      provides:
        "Reordered render() — Mode → Custom program → Persons → Climate entities"
    - path: frontend/src/components/person-card.ts
      provides: "Reordered render() — Presence mode → Schedule → Rooms"
    - path: custom_components/climate_manager/www/panel.js
      provides: "Rebuilt bundle reflecting room-card and person-card reorders"
  key_links:
    - from: coordinator.async_evaluate (MODE_OFF branch)
      to: _push_off_safely
      via:
        "passes period_temperatures[PERIOD_FROST_PROTECTION] as new frost_temp
        argument"
      pattern: "_push_off_safely\\(entity_id, desired_temp\\)"
    - from: _push_off_safely
      to: set_trv_temperature + set_trv_off
      via:
        "sequential awaits — temperature first, then hvac off; sentinel set only
        after both succeed"
      pattern: "await set_trv_temperature.*\\n.*await set_trv_off"
---

<objective>
Two backend behavior changes and two frontend reorder polish items for the off-mode handling and the expanded card layouts.

Purpose:

- Backend: when global mode flips to OFF and a TRV is off-capable, pre-set its
  setpoint to frost-protection BEFORE turning it off. This way, when the TRV
  later exits OFF, it does not resume an arbitrary stale setpoint — it lands on
  frost.
- Frontend: surface the most-used controls first on both room and person
  expanded cards (mode at the top, schedule next, associations/entities last).

Output:

- Updated `coordinator.py` `_push_off_safely` (new `frost_temp` param) +
  MODE_OFF dispatch passes it.
- Updated `tests/test_coordinator.py` asserting both calls happen for
  off-capable TRVs.
- Reordered render() in `room-card.ts` and `person-card.ts`.
- Rebuilt `custom_components/climate_manager/www/panel.js`. </objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/03-websocket-api-frontend-panel/03-CONTEXT.md
@custom_components/climate_manager/coordinator.py
@custom_components/climate_manager/trv.py
@tests/test_coordinator.py
@frontend/src/components/room-card.ts
@frontend/src/components/person-card.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — push frost-protection temp before hvac=off in MODE_OFF</name>
  <files>custom_components/climate_manager/coordinator.py, tests/test_coordinator.py</files>
  <behavior>
    - Test (update existing `test_mode_off_off_capable_trv_*` at line ~719 of tests/test_coordinator.py): when MODE_OFF dispatches and a TRV advertises `hvac_modes=['heat','off']`, BOTH `climate.set_temperature` (with the configured frost-protection temp) AND `climate.set_hvac_mode` (with `hvac_mode="off"`) are called for that entity. Assert ordering: set_temperature is observed before set_hvac_mode=off in the recorded service-call log.
    - Test (anti-flap regression — keep existing `test_mode_off_anti_flap_*` at line ~804): on a second tick in the same MODE_OFF state, neither set_temperature nor set_hvac_mode=off is re-issued (sentinel skip).
    - Test (heat-only regression — keep existing `test_mode_off_heat_only_trv_*` at line ~760): TRV without "off" in hvac_modes still receives only set_temperature(frost) via `_push_safely`, unchanged.
    - Test (mode-exit regression — keep existing `test_mode_off_to_time_program_*` at line ~846): switching MODE_OFF → MODE_TIME_PROGRAM still pushes heat + new setpoint.
  </behavior>
  <action>
    Modify `_push_off_safely(self, entity_id: str)` at coordinator.py:436 to accept a new `frost_temp: float` parameter: `async def _push_off_safely(self, entity_id: str, frost_temp: float) -> None`.
    Inside the function, AFTER the unavailable-state guard and the `_last_pushed[entity_id] == "off"` anti-flap guard, but BEFORE setting the sentinel:
      1. `await set_trv_temperature(self._hass, entity_id, frost_temp)` — wrap in the same try/except pattern as the existing call.
      2. `await set_trv_off(self._hass, entity_id)` — keep the existing call.
      3. On success of both, set `self._last_pushed[entity_id] = "off"` (sentinel only after both calls succeed; if set_trv_temperature raises, log a warning and STILL attempt set_trv_off so the safety behavior is preserved; if set_trv_off raises, do not set sentinel).
    Update the MODE_OFF dispatch at coordinator.py:114–120: change `self._push_off_safely(entity_id)` to `self._push_off_safely(entity_id, desired_temp)` (where `desired_temp` is already `period_temperatures[PERIOD_FROST_PROTECTION]`, computed two lines above).
    Update the docstring of `_push_off_safely` to describe the two-step behavior and rationale: "pre-set frost setpoint before hvac=off so resume from OFF lands on frost rather than the TRV's previous arbitrary setpoint."
    Update the off-capable MODE_OFF test (around line 719 in `tests/test_coordinator.py`) to assert both calls fire, with set_temperature ordered before set_hvac_mode=off. Inspect `hass.services.async_call` mock call list — use `call_args_list` order. Leave the heat-only test and the anti-flap test logic intact; the anti-flap test still asserts only ONE set_hvac_mode=off across two ticks (and you should add the symmetric assertion that only ONE set_temperature fires for the same entity across two ticks).
    Do NOT call `set_trv_temperature` via `_push_safely` (which updates `_last_pushed` with a float and would corrupt the "off" sentinel logic) — call the helper directly inside `_push_off_safely`.
  </action>
  <verify>
    <automated>cd /home/arnaud/dev/climate_manager && python -m pytest tests/test_coordinator.py -x -q -k "mode_off or MODE_OFF or off_to_time"</automated>
  </verify>
  <done>
    Off-capable TRV in MODE_OFF receives set_temperature(frost) THEN set_hvac_mode=off; anti-flap still suppresses both on repeat ticks; heat-only path unchanged; mode-exit transition unchanged. All four MODE_OFF tests in test_coordinator.py pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — reorder room-card and person-card expanded sections</name>
  <files>frontend/src/components/room-card.ts, frontend/src/components/person-card.ts</files>
  <action>
    `frontend/src/components/room-card.ts` — in `render()` (around lines 622–656), reorder the `card-content` block to this exact sequence:
      1. Mode selector — the existing `<div class="section-label">Mode</div>` + `<div class="select-wrapper"><select class="mode-select"…>` block (currently below the TRV/persons sections). Move it to the TOP of `card-content`.
      2. Custom time program — the existing `${resolvedMode === "custom" ? html`…<climate-manager-time-bar mode="schedule" …></climate-manager-time-bar>…<button class="reset-btn">Reset to global configuration</button>` block. Keep the time-bar and the reset button together, immediately AFTER the mode selector. Do NOT split them or duplicate the conditional.
      3. Persons section — `${this._renderPersonsSection()}` (unchanged content).
      4. Climate entities — `${this._renderTrvSection()}` (unchanged content). Immediately BEFORE this call, add `<div class="section-label">Climate entities</div>` so the TRV section has the same heading style as Mode. If `_renderTrvSection()` already emits its own internal header, leave its internals untouched but still add the new section-label outside it (read the helper first; if it has a duplicate header, remove the inner one and keep the new section-label as the single source).
    `frontend/src/components/person-card.ts` — in `render()` (lines 402–467), reorder the `card-content` block to:
      1. Presence mode selector — keep the existing `<div class="section-label">Presence mode</div>` + `<select class="mode-select">…</select>` block at the top (unchanged position).
      2. Presence schedule — move the `${isScheduled ? html`<div class="section-label">Presence schedule</div>…<climate-manager-time-bar mode="presence" …></climate-manager-time-bar>…<button class="reset-btn">Reset to default</button>` block UP so it appears immediately after the presence mode selector. Keep the time-bar + reset button together; keep the conditional guard `isScheduled` unchanged.
      3. Room associations — move the existing `<div class="section-label">Room associations</div>` + chips + search-picker block DOWN so it now appears LAST.
    Do not change any CSS, save handlers, or save payloads — markup order only. Do not introduce or remove any sections.
  </action>
  <verify>
    <automated>cd /home/arnaud/dev/climate_manager/frontend && npx tsc --noEmit</automated>
  </verify>
  <done>
    Both `render()` methods compile with `tsc --noEmit` (0 errors). Section ordering in source matches the spec above. No other behavior changes (handlers, props, CSS untouched).
  </done>
</task>

<task type="auto">
  <name>Task 3: Build — regenerate panel bundle</name>
  <files>custom_components/climate_manager/www/panel.js</files>
  <action>
    Run `npm run build` from the `frontend/` directory. The Vite build emits to `custom_components/climate_manager/www/panel.js` (per existing build config). Verify the build completes with exit code 0 and no TypeScript or Lit errors in stdout/stderr.
    If the build emits warnings only, they are acceptable; if it emits errors, return to Task 2 and fix them before re-running.
    Do not edit `panel.js` by hand — it is a generated artifact.
  </action>
  <verify>
    <automated>cd /home/arnaud/dev/climate_manager/frontend && npm run build 2>&1 | tail -20 && test -f /home/arnaud/dev/climate_manager/custom_components/climate_manager/www/panel.js</automated>
  </verify>
  <done>
    `npm run build` exits 0; `custom_components/climate_manager/www/panel.js` exists and was modified by this build run (newer mtime than before the task started).
  </done>
</task>

</tasks>

<verification>
- `python -m pytest tests/test_coordinator.py -x -q` — all coordinator tests pass (no regressions in non-MODE_OFF tests either).
- `cd frontend && npx tsc --noEmit` — 0 TypeScript errors.
- `cd frontend && npm run build` — 0 errors; panel.js rebuilt.
- Grep sanity check: `grep -n "_push_off_safely" custom_components/climate_manager/coordinator.py` — exactly two occurrences (definition + dispatch call site), both with two arguments.
</verification>

<success_criteria>

- Backend: MODE_OFF on off-capable TRV → set_temperature(frost) followed by
  set_hvac_mode=off; anti-flap preserved; heat-only path unchanged.
- Coordinator test updated to assert both calls and their ordering; all existing
  MODE_OFF tests still pass.
- Room card expanded body section order: Mode → Custom program (conditional) →
  Persons → Climate entities.
- Person card expanded body section order: Presence mode → Presence schedule
  (conditional) → Room associations.
- `panel.js` regenerated with 0 build errors. </success_criteria>

<output>
Create `.planning/quick/260526-plq-off-mode-push-frost-protection-temp-befo/260526-plq-SUMMARY.md` when done, listing:
- Files modified (coordinator.py, test_coordinator.py, room-card.ts, person-card.ts, panel.js)
- Behavioral changes (frost-then-off ordering; section reorders)
- Test results (pytest output line, build output line)
</output>
