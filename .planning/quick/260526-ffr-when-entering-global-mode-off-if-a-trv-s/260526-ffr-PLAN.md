---
phase: quick-260526-ffr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - custom_components/climate_manager/trv.py
  - custom_components/climate_manager/coordinator.py
  - tests/test_trv.py
  - tests/test_coordinator.py
autonomous: true
requirements:
  - GLOBAL-02
must_haves:
  truths:
    - "When entering MODE_OFF, TRVs that advertise HVACMode.OFF in their
      `hvac_modes` attribute are commanded to OFF (no temperature setpoint
      pushed)"
    - "When entering MODE_OFF, TRVs that do NOT advertise HVACMode.OFF receive
      the frost-protection setpoint (current behaviour) via the existing
      two-call sequence"
    - "When leaving MODE_OFF (next evaluation tick in any other global mode),
      TRVs that advertise HVACMode.HEAT are first switched back to HEAT before
      the new setpoint is applied (the existing two-call sequence already does
      this)"
    - "Off-capable TRVs are not flapped: a second evaluation while still in
      MODE_OFF does not re-issue set_hvac_mode=off to the same entity"
  artifacts:
    - path: "custom_components/climate_manager/trv.py"
      provides:
        "new helper `set_trv_off(hass, entity_id)` that issues
        climate.set_hvac_mode=off when supported"
    - path: "custom_components/climate_manager/coordinator.py"
      provides:
        "MODE_OFF branch dispatches per-TRV between set_trv_off (off-capable)
        and set_trv_temperature (frost-protection fallback)"
  key_links:
    - from: "coordinator.async_evaluate (MODE_OFF branch)"
      to: "trv.set_trv_off"
      via: "per-entity capability check on hvac_modes attribute"
      pattern: "HVACMode\\.OFF in .*hvac_modes"
---

<objective>
When the global mode is set to **Off**, the integration should put each TRV into its native OFF state when the device supports it, and only fall back to pushing the frost-protection setpoint when the TRV cannot be turned off. When the global mode leaves Off, TRVs that support HEAT must be returned to HEAT before any setpoint is applied (this already happens via the existing two-call sequence in `set_trv_temperature`, but the new path must not regress it).

Purpose: today the MODE_OFF branch always pushes frost-protection (5°C) via the
two-call HEAT + set_temperature sequence. On TRVs that support HVACMode.OFF
(most modern Z-Wave / Zigbee / Matter TRVs, including the Tado X which exposes
both `heat` and `off`), this leaves the valve actively heating to 5°C instead of
being closed. The user wants real "off" when the device supports it, and the
existing fallback otherwise.

Output: an updated `trv.py` with a `set_trv_off` helper + capability check, and
a coordinator MODE_OFF branch that dispatches per-TRV between the two paths.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@custom_components/climate_manager/trv.py
@custom_components/climate_manager/coordinator.py
@custom_components/climate_manager/const.py
@tests/test_trv.py
@tests/test_coordinator.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add OFF-capable TRV helper in trv.py</name>
  <files>custom_components/climate_manager/trv.py, tests/test_trv.py</files>
  <behavior>
    - `supports_hvac_off(hass, entity_id)` returns True iff `hass.states.get(entity_id).attributes["hvac_modes"]` contains the string `"off"` (HVACMode.OFF.value). Missing state, missing `hvac_modes` attribute, or `"off"` not in the list → False.
    - `set_trv_off(hass, entity_id)` issues exactly one `climate.set_hvac_mode` call with `hvac_mode="off"`, `blocking=True`, and no `set_temperature` call.
    - `set_trv_off` is a no-op (zero service calls) when the entity state is None or `"unavailable"` (mirrors `set_trv_temperature` ROOM-03 guard).
    - Existing `set_trv_temperature` behaviour MUST remain unchanged — it still issues set_hvac_mode=heat then set_temperature. This means TRVs leaving MODE_OFF that support HEAT are returned to HEAT by the very next push (no new code path needed for the "leaving off" direction).
  </behavior>
  <action>
    In `custom_components/climate_manager/trv.py`:
    1. Import `HVACMode` from `homeassistant.components.climate.const` at the top of the module.
    2. Add `def supports_hvac_off(hass: HomeAssistant, entity_id: str) -> bool` that reads `hass.states.get(entity_id)`, returns False if state is None, otherwise returns `HVACMode.OFF.value in (state.attributes.get("hvac_modes") or [])`. Do NOT raise on missing attribute — TRVs that don't expose the list are treated as not supporting off (fallback path).
    3. Add `async def set_trv_off(hass: HomeAssistant, entity_id: str) -> None` that guards on `state is None or state.state == "unavailable"` (silent return), then issues a single `hass.services.async_call("climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": HVACMode.OFF.value}, blocking=True)`. NO second call to set_temperature.
    4. Keep all existing module docstring sentinels (INFRA-04, ROOM-03, T-01-07, T-01-08) intact and reference them in the new helpers' docstrings where applicable.
    In `tests/test_trv.py` add four new tests:
    - `test_supports_hvac_off_true_when_off_in_hvac_modes`: seed state with `attributes={"hvac_modes": ["heat", "off"]}` → returns True.
    - `test_supports_hvac_off_false_when_attribute_missing`: seed state with empty attributes dict → returns False.
    - `test_set_trv_off_issues_single_set_hvac_mode_off_call`: seed available state, assert exactly one `set_hvac_mode` call with `hvac_mode="off"` and ZERO `set_temperature` calls.
    - `test_set_trv_off_skips_unavailable_entity`: seed `"unavailable"` state → zero service calls.
    Use the existing `async_mock_service` + `CLIMATE_ENTITY` constant pattern from the file. Do NOT modify or replace any of the four existing tests in `test_trv.py`.
  </action>
  <verify>
    <automated>cd /home/arnaud/dev/climate_manager && .venv/bin/python -m pytest tests/test_trv.py -x -q</automated>
  </verify>
  <done>All 8 tests in `tests/test_trv.py` pass (4 pre-existing + 4 new). `supports_hvac_off` and `set_trv_off` are importable from `custom_components.climate_manager.trv`. Existing `set_trv_temperature` source and tests are unchanged.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Dispatch per-TRV in coordinator MODE_OFF branch</name>
  <files>custom_components/climate_manager/coordinator.py, tests/test_coordinator.py</files>
  <behavior>
    - When `global_mode == MODE_OFF`, for each managed TRV entity_id the coordinator MUST:
      - call `set_trv_off(hass, entity_id)` if `supports_hvac_off(hass, entity_id)` is True
      - otherwise call `set_trv_temperature(hass, entity_id, frost_protection_temp)` (existing behaviour, unchanged)
    - The push-on-change discipline (`_last_pushed`) MUST be preserved for the frost-protection fallback path so unchanged TRVs aren't re-pushed every minute.
    - Off-capable TRVs MUST also be tracked so a second MODE_OFF tick does NOT re-issue set_hvac_mode=off. Use a sentinel value stored in `_last_pushed[entity_id]` that cannot collide with any real temperature (the string `"off"` is a safe sentinel — `_last_pushed` is currently typed `dict[str, float]` but is used by reference comparison only; widen the type to `dict[str, float | str]`).
    - When the user leaves MODE_OFF, the next tick's `set_trv_temperature` call (HEAT + set_temperature) clears the `"off"` sentinel by writing a float — no special "leaving off" code path is needed because the existing `_push_if_changed` comparison `last == desired_temp` is False for `"off" == 20.0`, so the push fires. The two-call sequence in `set_trv_temperature` will set HVAC mode back to HEAT before set_temperature.
    - Non-TRV entities (boilers, HVAC units) MUST continue to be skipped (the MODE_OFF branch currently pushes to ALL entities in rooms — keep that behaviour but add `is_trv_entity` filtering only if it was already absent; do not change scope of which entities are touched relative to existing behaviour).
  </behavior>
  <action>
    In `custom_components/climate_manager/coordinator.py`:
    1. Update the import line `from .trv import is_trv_entity, set_trv_temperature` to also import `set_trv_off, supports_hvac_off`.
    2. Widen the `_last_pushed` annotation in `__init__` to `dict[str, float | str]`.
    3. Refactor the MODE_OFF branch (lines ~110-117) so the `asyncio.gather` iterates entity_ids and chooses per-entity:
       - if `supports_hvac_off(self._hass, entity_id)`: schedule `self._push_off_safely(entity_id)`
       - else: schedule `self._push_safely(entity_id, desired_temp, "MODE_OFF")` (existing fallback)
       Keep the existing `desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]` line — it's still the fallback value.
    4. Add a new method `async def _push_off_safely(self, entity_id: str) -> None` that mirrors `_push_safely`/`_push_if_changed` but for the off path:
       - guard on `state is None or state.state == "unavailable"` (skip)
       - if `self._last_pushed.get(entity_id) == "off"`: return (no flapping)
       - call `await set_trv_off(self._hass, entity_id)` wrapped in try/except logging "Failed to push OFF to %s in MODE_OFF" on failure
       - on success record `self._last_pushed[entity_id] = "off"`
    5. Leave status-payload code (`_last_active_period = None`, `_last_present_persons`, status_update fire) untouched — those still apply identically.
    In `tests/test_coordinator.py` add three new tests near the existing MODE_OFF coverage:
    - `test_mode_off_uses_set_hvac_mode_off_when_supported`: seed climate state with `attributes={"hvac_modes": ["heat", "off"], "temperature": 18.0}`, mock both `set_hvac_mode` and `set_temperature`, set `runtime_config["global_mode"] = MODE_OFF`, run `async_evaluate`. Assert at least one `set_hvac_mode` call with `hvac_mode="off"` for our entity AND zero `set_temperature` calls for our entity.
    - `test_mode_off_falls_back_to_frost_temp_when_off_not_supported`: seed state with `attributes={"hvac_modes": ["heat"], "temperature": 18.0}`, run MODE_OFF evaluate. Assert at least one `set_temperature` call for our entity with `temperature == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]` (5.0) and that any `set_hvac_mode` calls for our entity use `hvac_mode="heat"` (not `"off"`).
    - `test_mode_off_does_not_flap_set_hvac_mode_off_on_repeat_tick`: like the first test, but call `async_evaluate` twice in a row without changing state. Assert the total count of `set_hvac_mode={hvac_mode:"off"}` calls for our entity equals 1, not 2.
    Use the existing `_make_runtime_config` helper with `global_mode=MODE_OFF`.
  </action>
  <verify>
    <automated>cd /home/arnaud/dev/climate_manager && .venv/bin/python -m pytest tests/test_coordinator.py tests/test_trv.py -x -q</automated>
  </verify>
  <done>All existing coordinator tests still pass. The three new MODE_OFF dispatch tests pass. Manual smoke-read of the diff confirms only the MODE_OFF branch in `async_evaluate` and the new `_push_off_safely` method were added; no other branch (MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES) was touched.</done>
</task>

</tasks>

<verification>
- `pytest tests/test_trv.py tests/test_coordinator.py -x -q` is green (full suite previously green; only additions made).
- Manual diff inspection: `set_trv_temperature` is byte-identical to its pre-change form; only new symbols added in `trv.py`.
- Manual diff inspection: in `coordinator.py`, only the MODE_OFF branch inside `async_evaluate` is modified, plus the import line and `_last_pushed` annotation, plus the new `_push_off_safely` method.
</verification>

<success_criteria>

- An off-capable TRV (Tado X exposing `hvac_modes=["heat","off"]`) in MODE_OFF
  receives `climate.set_hvac_mode hvac_mode=off` and no `set_temperature` call.
- A TRV that does not expose `"off"` in `hvac_modes` continues to receive
  frost-protection setpoint (5.0°C) via the existing HEAT + set_temperature
  two-call sequence (no regression on GLOBAL-02).
- Leaving MODE_OFF: the very next evaluation in MODE_TIME_PROGRAM or
  MODE_TIME_PROGRAM_PRESENCES causes `set_trv_temperature` to fire, which by
  construction calls `set_hvac_mode=heat` first and then the new setpoint —
  restoring HEAT mode on devices that need it.
- Repeated MODE_OFF ticks do not re-emit `set_hvac_mode=off` for the same entity
  (push-on-change parity with the existing temperature path).
  </success_criteria>

<output>
Create `.planning/quick/260526-ffr-when-entering-global-mode-off-if-a-trv-s/260526-ffr-SUMMARY.md` when done.
</output>
