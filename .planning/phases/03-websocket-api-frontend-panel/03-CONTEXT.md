# Phase 3: WebSocket API & Frontend Panel - Context

**Gathered:** 2026-05-17 (updated 2026-05-20)
**Status:** Ready for planning

<domain>
## Phase Boundary

A full Lovelace dashboard panel that lets users configure every aspect of the integration — global mode, default temperatures, global and per-room time programs, persons presence mode and schedules, room sensor associations — without touching YAML or HA config files. A Python WebSocket API layer exposes the backend config and coordinator to the Lit/TypeScript panel via `homeassistant.components.websocket_api`.

Requirements in scope: UI-01, UI-02, UI-03, UI-04, ROOM-01, ROOM-02, ROOM-03, INFRA-01.

**Pre-condition — schema refactor required before Phase 3 begins:**
The Phase 2 backend uses a `weekday_groups` schema for time programs. Phase 3 requires a per-day schema (`{"mon": [...], "tue": [...], ...}`). A gap-closure plan must refactor `schedule.py`, `const.py`, `DEFAULT_CONFIG`, and all tests before any Phase 3 work begins. The panel UI and WebSocket API are designed against the per-day schema exclusively.

</domain>

<decisions>
## Implementation Decisions

### Time Program Editor

- **D-01:** Per-day time program schema — `{"mon": [...], "tue": [...], "wed": [...], "thu": [...], "fri": [...], "sat": [...], "sun": [...]}` — replaces the Phase 2 `weekday_groups` structure. Each day holds an independent list of periods `[{"start": "HH:MM", "mode": "<period_mode>"}, ...]`. Both the global time program and per-room overrides use this format. Applies to person presence schedules too.
- **D-02:** Visual 24h bar editor — all 7 days stacked vertically, one colored bar per row, full week visible at once without tabs or scrolling.
- **D-03:** Period colors: Frost protection = deep blue, Reduced = light blue, Normal = orange, Comfort = red. Presence schedule: Present = green, Absent = gray.
- **D-04:** Click anywhere on the bar → splits the existing period at that time (snaps to nearest 15 min) → small popup appears: "Split at HH:MM" with 4 colored mode choices. User selects the mode for the new segment.
- **D-05:** Click an existing block → popup shows the period's time range, current mode, [Change mode] and [Delete] buttons. Delete merges the block into the left (preceding) neighbor — preceding period expands to fill.
- **D-06:** Drag the border between two adjacent blocks to adjust the transition time. A tooltip shows the exact time (HH:MM) during drag. No save fires during drag — save fires on mouse-up.
- **D-07:** [Copy] and [Paste] buttons on the right of each day row. [Copy] stores that day's schedule in panel-local clipboard state. [Paste] on any other day applies the copied schedule. One-click-per-target — no dropdown.

### Save Model

- **D-08:** Auto-save on every field change — no explicit Save button anywhere in the panel. Every global mode switch, temperature input, presence mode change, room override toggle, and person/room association change fires a WebSocket save command immediately.
- **D-09:** Time program bar saves on interaction end, not during editing: mouse-up after a drag, popup close after a split/edit/delete, paste button click. This prevents flooding the WebSocket with intermediate states during a drag.
- **D-10:** Save feedback via toast/snackbar: "✓ Saved" (appears briefly then fades) on success. "✗ Save failed — retrying..." on error. Non-blocking — matches HA's own notification style.
- **D-11:** No "Applied" confirmation after the coordinator pushes to TRVs. Save confirmation is sufficient — the coordinator re-evaluates within the next poll cycle.

### Panel Navigation

- **D-12:** Top-level navigation: three tabs — `[Global Settings]` `[Rooms]` `[Persons]`. Standard HA tab pattern.
- **D-13:** Global Settings tab layout: a read-only **Current Status** section at the top (current global mode, active period name + end time, present persons with green dots), followed by the **Configuration** section (mode selector dropdown, default temperature inputs for all 4 period modes, global time program editor).
- **D-14:** Rooms tab: expandable cards per room. Collapsed card shows room name + program badge ("global program" or "custom program"). Expanded card shows: associated TRV entity IDs, "Override global time program" toggle, and (when override is enabled) the inline 7-bar editor. Room cards with a custom time program are expanded by default; all others are collapsed by default.
- **D-14a (ordering — updated 2026-05-20):** Rooms are ordered by floor then room name, matching the HA climate panel. Floor names appear as section headers between floor groups (e.g. "Ground floor", "First floor"). Floors are ordered by their `level` field from `hass.floors` (ascending integer). Within a floor, rooms are sorted alphabetically by name. Rooms with no floor assignment appear after all floored rooms, in alphabetical order, without a section header. This replaces the previous custom-program-first ordering — program type no longer affects sort position.
- **D-14b (data source — Claude's discretion):** Floor and area data comes from `hass.areas` (each area has a `floor_id` field) and `hass.floors` (each floor has `floor_id`, `name`, `level`). No backend changes needed — all ordering is done in `rooms-tab.ts`. The `Hass` TypeScript interface must be extended with `areas: Record<string, { area_id: string; name: string; floor_id: string | null }>` and `floors: Record<string, { floor_id: string; name: string; level: number }>`.
- **D-15:** Persons tab: expandable cards per person. Collapsed card shows name + presence mode badge (Automatic / Present / Absent). Expanded card shows: presence mode selector, room association checkboxes (one per discovered room), and the presence schedule bar editor (same 7-bar format with Present=green and Absent=gray blocks). Persons with any non-default setting are listed first (Phase 1 D-18) and expanded by default. Fully-default persons are listed after, collapsed by default.

### Room Status & Sensor Configuration

- **D-16:** Each room supports two optional sensor entity IDs stored in the room's config: `temperature_sensor` (a `sensor.*` entity for room air temperature) and `humidity_sensor` (a `sensor.*` entity for room humidity). These are set by the user in the room card's expanded view.
- **D-17:** Live room status display in the Rooms tab: current temperature (from `temperature_sensor` if defined, else from TRV's `current_temperature` attribute), current humidity (from `humidity_sensor` if defined, else not shown), and active period name. These values are read-only in the UI.
- **D-18:** Present persons shown only on the Global Settings tab (in the Current Status section). Not duplicated on the Rooms tab.

### Claude's Discretion

- WebSocket command granularity: whether to use one command per field (e.g., `climate_manager/set_global_mode`) or section-level saves (e.g., `climate_manager/save_global_settings`) — left to the researcher/planner to design the minimal command set that supports auto-save.
- Frontend build integration: how Vite build output is placed in `custom_components/climate_manager/www/` and how `make deploy` is extended to include a build step — left to the planner.
- `async_register_panel` signature: verify against current HA source before implementation (noted in STATE.md blockers).
- Whether Lit is bundled into `panel.js` or uses HA's Lit instance — bundling is safer (avoids version conflicts), noted as the default approach in CLAUDE.md.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements & Decisions
- `specs.md` — Full feature specification: period modes, time program structure, person presence modes, use cases
- `.planning/PROJECT.md` — Project context, key decisions (heat mode, sparse storage, v1 presence = periodic schedule, SSH deploy)
- `.planning/REQUIREMENTS.md` — All v1 requirements; Phase 3 scope: UI-01–04, ROOM-01–03, INFRA-01
- `.planning/phases/02-backend-engines-coordinator/02-CONTEXT.md` — Phase 2 decisions: coordinator, push-on-change, manual override, presence logic
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions: storage schema, discovery model (area_id as room key, person.* as person key), D-17/D-18 ordering rules

### Phase 2 Backend (Phase 3 reads and writes via these)
- `custom_components/climate_manager/__init__.py` — `ClimateManagerData`, `entry.runtime_data` pattern, `async_setup_entry` / `async_unload_entry`
- `custom_components/climate_manager/const.py` — Full v1 schema, `DEFAULT_CONFIG`, period/mode constants
- `custom_components/climate_manager/coordinator.py` — `ClimateManagerCoordinator.async_evaluate()` — call after config save to apply immediately
- `custom_components/climate_manager/storage.py` — `ClimateManagerStore.async_save(config)` — Phase 3 WebSocket handlers write via this
- `custom_components/climate_manager/discovery.py` — `discover_rooms()` / `discover_persons()` — Phase 3 needs their output for panel data

### Tech Stack & Architecture
- `CLAUDE.md` — Technology stack: Lit 3.x + TypeScript + Vite for panel, `homeassistant.components.websocket_api` for API, `frontend.async_register_panel` for panel registration, bundled Lit (not shared HA instance)
- `.planning/research/STACK.md` — Full stack rationale (if exists)
- `.planning/research/PITFALLS.md` — Critical pitfalls including ghost listeners (Pitfall 1), blocking I/O (Pitfall 2)

### HA Developer APIs
- HA Developer Docs: `homeassistant.components.websocket_api` — custom WebSocket command registration
- HA Developer Docs: `frontend.async_register_panel` — Lovelace panel registration (`module_url`, sidebar config)
- HA Developer Docs: `hass.states.get(entity_id)` — reading sensor/person entity states for live status
- `home-assistant-js-websocket` — panel-side WebSocket client (`hass.connection.subscribeMessage`, `sendMessagePromise`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClimateManagerStore.async_save(config)` — Phase 3 WebSocket handlers call this after any mutation to persist. Already handles deep-merge and sparse storage.
- `ClimateManagerCoordinator.async_evaluate()` — Call after saving config to trigger an immediate re-evaluation (rather than waiting for the next minute poll).
- `entry.runtime_data.runtime_config` — The in-memory merged config dict. WebSocket read handlers return slices of this; write handlers mutate it and call `async_save`.
- `discover_rooms(hass)` and `discover_persons(hass)` — Already implemented. Phase 3 calls these on panel load to populate the rooms/persons lists.

### Established Patterns
- **Sparse storage**: Only store non-default values. WebSocket save handlers must preserve this — read current stored data, apply the mutation, write back. Never write full DEFAULT_CONFIG with every save.
- **`entry.runtime_data` as integration spine**: WebSocket handlers access all state via `entry.runtime_data`. No global `hass.data` dict.
- **Discovery = source of truth for structure**: Room and person identity comes from HA registries (area_id, person.* entity_id). Storage only holds configuration deltas.
- **Two-call TRV control**: Already in `trv.set_trv_temperature()`. Phase 3 does not call this directly — it mutates config and lets the coordinator push.

### Integration Points
- `async_setup_entry` in `__init__.py` — Phase 3 adds WebSocket command registration and `async_register_panel` call here.
- `async_unload_entry` in `__init__.py` — WebSocket commands auto-unregister with the config entry; no explicit cleanup needed.
- `ClimateManagerData` dataclass — May need a `rooms_meta` field or similar to cache discovered room sensor associations; or discovery can be called inline per WebSocket request.
- The per-day schema refactor (pre-condition) changes `const.py`'s `DEFAULT_CONFIG` shape and `schedule.py`'s evaluation logic — all Phase 3 code is written against the refactored schema.
- **`frontend/src/types.ts` `Hass` interface** — Must be extended with `areas` and `floors` registry maps for floor-based room ordering (D-14b). `hass.areas[area_id].floor_id` is null for unassigned areas; guard for this in sort logic.

</code_context>

<specifics>
## Specific Ideas

- **Reference UI**: Tado app uses per-day scheduling — same pattern confirmed by user. The 7-bar stacked layout mirrors Tado's week view.
- **Interaction model**: The time bar is always fully covered (no gaps — the period before the first defined start implicitly extends from 00:00). Clicking splits the bar; the leftmost block always starts at 00:00.
- **Tooltip during drag**: Shows exact time in `HH:MM` format (e.g., "10:15") while dragging a period boundary.
- **Mode popup**: Appears on click (both on empty bar for split, and on existing block for edit/delete). Shows colored squares matching D-03 colors next to each mode name.
- **Global status strip**: Shows "Active period: Normal (until 22:00)" — period name + end time. Derived from coordinator's last evaluation result.
- **Room sensor fields**: Shown in the expanded room card as optional text inputs for `temperature_sensor` and `humidity_sensor` entity IDs. User types or pastes entity IDs (e.g., `sensor.bedroom_temperature`). No entity picker required in v1.
- **Presence schedule bar**: Uses the same 7-bar component as the time program editor, parameterized for 2 modes (Present/Absent) instead of 4. Green = present, gray = absent.

</specifics>

<deferred>
## Deferred Ideas

- **TRV availability indicator** (reachable/unreachable dot per TRV entity) — useful but not in requirements. Deferred to v2 — requires subscribing to each TRV entity state.
- **Entity picker for sensor fields** — a searchable dropdown of `sensor.*` entities rather than a plain text input. v2 UX improvement.
- **"Applied" confirmation** — showing "✓ Applied to TRVs" after the coordinator pushes. Decided against (D-11) — save toast is sufficient for v1.
- **Auto-detect humidity sensors** — auto-discover `sensor.*_humidity` in the same area_id. v2 quality-of-life feature.

</deferred>

---

*Phase: 3-WebSocket API & Frontend Panel*
*Context gathered: 2026-05-17*
