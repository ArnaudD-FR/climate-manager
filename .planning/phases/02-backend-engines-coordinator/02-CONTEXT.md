# Phase 2: Backend Engines & Coordinator - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

All heating logic — the schedule evaluator, global mode switcher, person presence tracker, and coordinator control loop. The coordinator runs on a polling tick, derives the active period from the current wall-clock time, and pushes temperatures to TRVs only when the target changes. No WebSocket API, no HA entities, no frontend — those are Phase 3.

Requirements in scope: GLOBAL-01, GLOBAL-02, GLOBAL-03, SCHED-01, SCHED-02, SCHED-03, SCHED-04, SCHED-05, PERSON-01, PERSON-02, PERSON-03, PERSON-04, PERSON-05, PERSON-06, PERSON-07, PERSON-08, PERSON-09, INFRA-03, INFRA-05. Plus new requirements identified in this discussion (D-06, D-07, D-08 — see Decisions).

</domain>

<decisions>
## Implementation Decisions

### Scheduler Trigger

- **D-01:** Poll every minute via `async_track_time_interval(hass, coordinator.async_evaluate, timedelta(minutes=1))`. Each tick calls `dt_util.now()` and derives the active period from the current wall-clock time. DST-safe by construction — no pre-scheduled boundary times, no re-scheduling logic needed (INFRA-05).
- **D-02:** Push-on-change only — the coordinator tracks `_last_pushed: dict[str, float]` (entity_id → last pushed temperature). A TRV service call is issued only when the computed target temperature differs from the last pushed value. This prevents unnecessary service calls and avoids battery drain from minute-level command frequency.
- **D-03:** Manual override hold — if the TRV currently reports a temperature different from `_last_pushed[entity_id]`, the user has manually adjusted the TRV. Skip this entity for this tick. At the next period transition (when `desired_temp ≠ _last_pushed[entity_id]`), the coordinator resumes control and pushes the new scheduled temperature. The hold lifts automatically without any explicit release mechanism.
- **D-04:** On HA restart, `_last_pushed` is empty. INFRA-03 applies: the coordinator immediately evaluates from current wall-clock time and pushes the correct temperature to all TRVs, overriding any prior manual state.

### Presence Edge Cases

- **D-05:** When a person is Present (any mode) and their room's active time program has no Normal or Comfort periods for the current day → apply Reduced temperature. Presence "fills in" Normal/Comfort gaps (PERSON-08), but cannot create Normal heat where the schedule defines none.
- **D-06:** **New requirement** — Time programs must cover all 7 days (Mon–Sun). Each day must appear in exactly one weekday group. Validated at save time; programs with any missing day or duplicate-assigned day are rejected. Extends SCHED-04 ("at most one") to "exactly one" across the full week.
- **D-07:** Any person with no room associations configured → skip silently, regardless of whether they have schedule/mode settings. No backend warning, no log entry. Expected state for newly discovered or partially-configured persons. (A UI warning badge in the Phase 3 panel when a person has settings but no rooms is a Phase 3 concern — deferred.)

### Phase 2 HA Entities

- **D-09:** Pure backend — no HA entities (no select, no sensor, no switch) in Phase 2. All UI is Phase 3. Hardware testing during Phase 2 is done via HA Developer Tools (call services, inspect logs), not via UI entities.

### Claude's Discretion

- Coordinator class structure: how `_last_pushed` is stored, whether the coordinator is a standalone class or a method on ClimateManagerData, how the scheduler listener is registered/cleaned up on unload — left to the planner/researcher.
- Evaluation order within a tick: whether rooms are evaluated sequentially or in parallel — left to the planner.
- How `dt_util.now()` is used for weekday/time resolution (timezone conversion, day-of-week lookup) — standard HA pattern, researcher should verify against HA core.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements & Decisions
- `specs.md` — Full feature specification: definitions, period modes, time program structure, person presence modes, use cases (PERSON-07/08/09 sandwiched-gap rule)
- `.planning/PROJECT.md` — Project context, key decisions (heat mode only, sparse storage, v1 presence = periodic schedule)
- `.planning/REQUIREMENTS.md` — All v1 requirements with REQ-IDs; Phase 2 scope: GLOBAL-01–03, SCHED-01–05, PERSON-01–09, INFRA-03, INFRA-05
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions that carry forward: two-call TRV control, sparse storage, area_id = room key, person.* entity_id = person key, runtime_data pattern

### Phase 1 Implemented Modules (Phase 2 uses these directly)
- `custom_components/climate_manager/const.py` — Full v1 schema: period modes, global modes, DEFAULT_CONFIG, DEFAULT_PERIOD_TEMPERATURES
- `custom_components/climate_manager/trv.py` — `set_trv_temperature(hass, entity_id, temperature)` — two-call sequence with availability guard (already implemented; Phase 2 calls this)
- `custom_components/climate_manager/storage.py` — `ClimateManagerStore.async_load()` / `async_save()` — sparse-merge Store layer
- `custom_components/climate_manager/__init__.py` — `ClimateManagerData` dataclass, `entry.runtime_data` pattern, PLATFORMS list (Phase 2 wires coordinator into setup/unload)
- `custom_components/climate_manager/discovery.py` — `discover_rooms()` / `discover_persons()` — area/entity registry discovery

### HA Developer APIs
- HA Developer Docs: `homeassistant.helpers.event.async_track_time_interval` — used for the polling scheduler
- HA Developer Docs: `homeassistant.util.dt.now()` (`dt_util.now()`) — always-correct wall-clock time, DST-aware
- HA Developer Docs: `homeassistant.config_entries.ConfigEntry` + `entry.runtime_data` — where coordinator is stored/cleaned up on unload

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `trv.set_trv_temperature(hass, entity_id, temperature)` — already handles availability guard (skip if state is None or "unavailable"). Phase 2 calls this directly; no wrapper needed.
- `ClimateManagerStore.async_load()` — returns merged config (DEFAULT_CONFIG + sparse stored delta). Phase 2 reads `entry.runtime_data.runtime_config` for global_mode, period_temperatures, global_time_program, rooms, persons.
- `ClimateManagerData` dataclass — Phase 2 extends this with a `coordinator` field (or adds coordinator registration via a separate mechanism). Keep runtime_data as the single source of in-memory state.

### Established Patterns
- **Sparse storage**: only non-default values are stored. Phase 2 reads config via `entry.runtime_data.runtime_config`; writes via `entry.runtime_data.store.async_save(updated_config)`.
- **Push-on-change** (new in Phase 2): coordinator only calls `set_trv_temperature` when desired temp ≠ last pushed temp. Internal `_last_pushed` dict tracks this per entity.
- **Runtime_data = integration spine**: Phase 2 adds the coordinator reference to `entry.runtime_data`. Phase 3 will call methods on the coordinator via `entry.runtime_data.coordinator`.
- **No ghost listeners**: `async_unload_entry` must cancel the `async_track_time_interval` listener. This is Pitfall 1 from Phase 1 RESEARCH — ensure the scheduler listener is stored and cancelled on unload.

### Integration Points
- `async_setup_entry` in `__init__.py` — Phase 2 adds coordinator construction and scheduler registration here (after store load + discovery).
- `async_unload_entry` in `__init__.py` — Phase 2 adds scheduler cancellation here.
- `ClimateManagerData` dataclass — Phase 2 adds a `coordinator` field (or a cancel callback) to enable clean unload and Phase 3 access.
- `PLATFORMS` list — stays empty in Phase 2 (pure backend, no entity platforms).

</code_context>

<specifics>
## Specific Ideas

- **Polling interval:** 60 seconds via `timedelta(minutes=1)`. This is the evaluation cadence — TRV commands are pushed at most once per minute per entity, but in practice only on period transitions.
- **Manual override detection:** compare `hass.states.get(entity_id).attributes.get("temperature")` with `_last_pushed[entity_id]`. If they differ → user overrode → skip. At next period transition (desired_temp changes) → push regardless, resuming control.
- **Restart recovery (INFRA-03):** call `coordinator.async_evaluate()` immediately after registration in `async_setup_entry` — before the first polling tick fires — to push the correct temperature right on startup.
- **Time program completeness validation (D-06):** at save time, verify `{Mon, Tue, Wed, Thu, Fri, Sat, Sun} == union of all days across all weekday_groups`. Reject if any day missing or duplicated. This validation applies to both the global time program and any per-room overrides.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 3 UI warning badge** — When a person has schedule/mode configured but no room associations, show a warning indicator next to their name in the Persons panel. (Phase 3 scope — the panel doesn't exist yet.)
- **Configurable polling interval** — Allow users to set the evaluation cadence (e.g., 1 min, 5 min) via global settings. Deferred to v2 — 60s is appropriate for Phase 1 hardware.
- **Presence override entities** — A select entity for global mode or per-person override entities in HA. Decided against in this phase (D-09). Could be added as a convenience feature in v2 without the full panel.

</deferred>

---

*Phase: 2-Backend Engines & Coordinator*
*Context gathered: 2026-05-16*
