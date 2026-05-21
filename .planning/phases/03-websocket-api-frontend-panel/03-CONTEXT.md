# Phase 3: WebSocket API & Frontend Panel - Context

**Gathered:** 2026-05-17 (updated 2026-05-20, 2026-05-20, 2026-05-20, 2026-05-21, 2026-05-21, 2026-05-21, 2026-05-21)
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

- **D-12 (updated 2026-05-21):** Top-level navigation: three tabs — `[Overview]` `[Rooms]` `[Persons]`. Tab formerly called "Global Settings" is now "Overview". Standard HA tab pattern.
- **D-13 (updated 2026-05-21):** Global Settings tab layout — three cards in order:
  1. **Current Status** (read-only) — current global mode, active period name + end time, present persons with green dots.
  2. **Temperatures** — the 4 period temperature inputs (Frost protection, Reduced, Normal, Comfort). Card title is exactly "Temperatures" (not "Default temperatures" or similar).
  3. **Configuration** — mode selector dropdown + global time program editor.
- **D-14:** Rooms tab: expandable cards per room. Collapsed card shows room name + mode badge. Expanded card shows: associated TRV entity IDs, a 3-option room mode selector, and (when Custom mode is selected) the inline 7-bar editor. Room cards with a custom time program are expanded by default; all others are collapsed by default. See D-20 for the full room mode specification.
- **D-14c (room card status — updated 2026-05-20):** The status summary (temperature, humidity, active period) is **always visible** on the room card, whether collapsed or expanded. It appears as a compact second line inside the card header area (below the room name + program badge row), using icons matching the existing status-row style (thermometer / water-percent / clock-outline). If temperature or humidity has no data (no sensor, no TRV reading), show "—" as placeholder. The `.status-row` inside the expanded `.card-content` section is **removed** to avoid duplication — the header line is the single source of status.
- **D-14d (room card person count — added 2026-05-21):** The room status line includes an assigned-persons count as a 4th status item (after temperature, humidity, active period). Uses `mdi:account-group` icon + integer count. Shows "0" when no persons are assigned — the count is always rendered so the 4-item status line is always complete. Data source: `_getAssignedPersonIds().length` (already available from `panelConfig.persons`). This is assignment count, not real-time presence (present persons remain on the Global Settings tab per D-18).
- **D-14a (ordering — updated 2026-05-20):** Rooms are ordered by floor then room name, matching the HA climate panel. Floor names appear as section headers between floor groups (e.g. "Ground floor", "First floor"). Floors are ordered by their `level` field from `hass.floors` (ascending integer). Within a floor, rooms are sorted alphabetically by name. Rooms with no floor assignment appear after all floored rooms, in alphabetical order, without a section header. This replaces the previous custom-program-first ordering — program type no longer affects sort position.
- **D-14b (data source — Claude's discretion):** Floor and area data comes from `hass.areas` (each area has a `floor_id` field) and `hass.floors` (each floor has `floor_id`, `name`, `level`). No backend changes needed — all ordering is done in `rooms-tab.ts`. The `Hass` TypeScript interface must be extended with `areas: Record<string, { area_id: string; name: string; floor_id: string | null }>` and `floors: Record<string, { floor_id: string; name: string; level: number }>`.
- **D-15 (updated 2026-05-21):** Persons tab: expandable cards per person. **All cards are always collapsed by default** — the previous "expanded if non-default" rule is removed.

  **Card header (collapsed state)** shows three elements in order:
  1. Person name
  2. Mode badge — shows current mode: "Scheduled", "HA", "Force Present", "Force Absent"
  3. Presence status dot — green (●) if currently present, gray (●) if absent. Derived from `status.present_persons.includes(personId)` (status pushed by subscribe_status). `status: StatusPayload | null` prop added to `person-card`; `persons-tab` passes `.status=${this.status}` to each card.

  **Card expanded state** shows: presence mode selector (4 options), room association chips, and the presence schedule bar editor (same 7-bar format, Present=green and Absent=gray — only visible when mode is "Scheduled").

### Room Status & Sensor Configuration

- **D-16 (revised 2026-05-20):** The room card does NOT expose sensor configuration fields. Sensor assignment is HA's responsibility, not Climate Manager's. Sensors are designated in HA Settings → Areas → [Room] → Temperature entity / Humidity entity. The `AreaEntry.temperature_entity_id` and `.humidity_entity_id` fields (introduced in HA 2026.5, confirmed present in production at `core.area_registry`) are the authoritative source. The `RoomConfig.temperature_sensor` / `.humidity_sensor` storage fields are removed — no manual sensor override via the panel.
- **D-17 (revised 2026-05-20):** Backend priority chain for room header temperature and humidity (applied in both `ws_get_status` in `websocket.py` and `_build_status_payload` in `coordinator.py`):
  1. `AreaEntry.temperature_entity_id` / `.humidity_entity_id` from HA area registry — use `getattr(area, 'temperature_entity_id', None)` to handle older HA dev venv gracefully.
  2. Fallback: auto-discovered sensor from `room_auto_sensors` (`discover_room_sensors` result).
  3. Temperature-only last resort: TRV `current_temperature` attribute (no humidity fallback from TRV).
  4. No data: return key absent from the room entry → frontend shows "—".
- **D-18:** Present persons shown only on the Global Settings tab (in the Current Status section). Not duplicated on the Rooms tab.

### Per-Room Mode

- **D-20 (added 2026-05-21):** Each room has an independent mode selector with 3 values, stored as `rooms[area_id].room_mode`:
  - **`"global"` (default)** — Room follows the global mode exactly (current default behavior). Default is sparse — absent key means `"global"`.
  - **`"frost_protection"`** — Room ignores the global program entirely. The coordinator holds `period_temperatures["frost_protection"]` (from the configurable Temperatures card, not hardcoded) for all TRVs in this room, permanently.
  - **`"custom"`** — Room has its own independent time program in `rooms[area_id].time_program`. When the user first switches a room to Custom mode (i.e., no `time_program` exists in the room's stored config), the current `global_time_program` is one-time copied into `rooms[area_id].time_program` as initial values. After that, the room program is fully independent — subsequent global program changes have no effect on it.

  **Coordinator changes:** For each room, read `room_mode = room_config.get("room_mode", "global")`. Branch:
    - `"frost_protection"`: push `period_temperatures[PERIOD_FROST_PROTECTION]` directly, no schedule evaluation.
    - `"global"`: use global time program (current default path — no code change for this branch).
    - `"custom"`: use `room_config["time_program"]` (same as existing override behavior).

  **Panel UI:** Replaces the "Override global time program" toggle in the expanded room card with a 3-option mode selector (native `<select>` — ha-select is broken in HA 2026.x). Selecting Custom reveals the inline 7-bar editor. When switching to Custom for the first time, the panel includes the current global program as the initial `time_program` value in the same `set_room_config` WebSocket call.

  **Badge text** in collapsed card header:
    - `"frost_protection"` → badge: **"Frost protection"**
    - `"global"` → badge: **"Global program"**
    - `"custom"` → badge: **"Custom program"**

  **Storage key added to `const.py`:** `ROOM_MODE_GLOBAL = "global"`, `ROOM_MODE_FROST = "frost_protection"`, `ROOM_MODE_CUSTOM = "custom"`.

### Presence Modes — Persons

- **D-21 (added 2026-05-21):** Four person presence modes replace the previous three. Stored as `persons[person_id].mode`:
  - `"scheduled"` — follow the person's periodic presence schedule (was "automatic", already migrated)
  - `"force_present"` — always present regardless of time or HA state (was "present")
  - `"force_absent"` — always absent (was "absent")
  - `"ha"` — presence is driven by HA's internal person entity: present when `hass.states[person_entity_id].state === "home"`, absent for all other states (`"not_home"`, zone names, `"unknown"`, `"unavailable"`).

  **Backend (`const.py`):** `PRESENCE_PRESENT = "force_present"`, `PRESENCE_ABSENT = "force_absent"`, add `PRESENCE_HA = "ha"`. `PRESENCE_AUTOMATIC = "scheduled"` already in place.

  **Backend (`schedule.py` `resolve_presence()`):** Update to use `PRESENCE_PRESENT = "force_present"` and `PRESENCE_ABSENT = "force_absent"`. HA mode (`"ha"`) is NOT handled in `resolve_presence()` — it's handled upstream in the coordinator, keeping the function pure (no `hass` param).

  **Backend (`coordinator.py` `_compute_present_persons()`):** Add `ha` mode branch: `hass_state = self.hass.states.get(person_id); if hass_state and hass_state.state == "home": present`. Called for all global modes to populate `_last_present_persons` for status display and TRV control.

  **Storage migration (`storage.py`):** On load, iterate `persons` and rename `"mode": "present"` → `"force_present"`, `"mode": "absent"` → `"force_absent"`. Analogous to the `"automatic"` → `"scheduled"` migration already in place.

  **Frontend (`person-card.ts`):** `PRESENCE_MODE_PRESENT = "force_present"`, `PRESENCE_MODE_ABSENT = "force_absent"`, add `PRESENCE_MODE_HA = "ha"`. Add 4th option to mode selector dropdown. Badge text: `"force_present"` → "Force Present", `"force_absent"` → "Force Absent", `"ha"` → "HA".

- **D-22 (added 2026-05-21):** Scheduled mode default schedule — applied one-time when a person switches TO `"scheduled"` mode and has no existing schedule (empty or absent `schedule` key). The panel includes the default schedule in the `set_person_config` call as initial values. Not stored in `DEFAULT_CONFIG`.

  Default schedule value:
  - Mon–Fri: `[{"start": "00:00", "state": "present"}, {"start": "08:00", "state": "absent"}, {"start": "18:00", "state": "present"}]`
  - Sat–Sun: `[{"start": "00:00", "state": "present"}]`

  Implementation: in `person-card.ts` `_onModeChange()`, when the selected value is `"scheduled"` and `this.config.schedule` is empty/absent, build the default schedule object and include it in the WebSocket save payload. Analogous to room Custom mode copying the global program on first switch (D-20).

### Assignment Picker

- **D-19 (added 2026-05-21):** Adding a person to a room (room card) and adding a room to a person (person card) both use a shared search-picker component — a floating popup with a search field + scrollable list, matching HA's native entity picker style. The current `<select>` dropdown is replaced.
  - **Trigger:** Same "+" chip button as today — clicking it opens the popup overlay.
  - **Person items** (in room card picker): person name (bold) + presence state as secondary text (e.g. "Home" / "Away" — from `hass.states[personId].state`).
  - **Room items** (in person card picker): room name (bold) + floor name as secondary text (e.g. "Ground floor" — from `hass.floors[area.floor_id].name`; omit if no floor assigned).
  - **Shared component:** One Lit component (e.g. `search-picker.ts`) parameterised with `items: Array<{id, label, secondary?, icon?}>`. Reused in both `room-card.ts` and `person-card.ts`.
  - **ha-select is broken in HA 2026.x** — implementation uses a native `<input type="text">` for search and a custom `<ul>` list, not any `ha-*` select component.
  - Items already assigned are excluded from the picker list (same logic as current `<select>` filtering).

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
- `_getAssignedPersonIds()` in `room-card.ts` — already computes persons assigned to a room; use `.length` for D-14d person count without new data fetching.
- Current add-person picker in `room-card.ts` and add-room picker in `person-card.ts` both use a native `<select>` — D-19 replaces both with the shared `search-picker` component.
- Room card "Override global time program" toggle in `room-card.ts` — D-20 replaces this boolean toggle with a 3-option `<select>` for room mode. The coordinator's `_evaluate_time_program` loop in `coordinator.py` needs a new branch for `room_mode == "frost_protection"` that pushes `period_temperatures[PERIOD_FROST_PROTECTION]` directly without schedule evaluation. `const.py` gains `ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`, `ROOM_MODE_CUSTOM` constants.
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
- **HA area sensor fields**: All rooms already have `temperature_entity_id` and `humidity_entity_id` set in HA area registry (verified on production HA 2026.5.3 — every managed area has sensors designated). Room card displays these read-only values via the backend priority chain (D-17). No manual input in the panel.
- **Presence schedule bar**: Uses the same 7-bar component as the time program editor, parameterized for 2 modes (Present/Absent) instead of 4. Green = present, gray = absent.

</specifics>

<deferred>
## Deferred Ideas

- **TRV availability indicator** (reachable/unreachable dot per TRV entity) — useful but not in requirements. Deferred to v2 — requires subscribing to each TRV entity state.
- **Entity picker for sensor fields** — a searchable dropdown of `sensor.*` entities rather than a plain text input. v2 UX improvement.
- **"Applied" confirmation** — showing "✓ Applied to TRVs" after the coordinator pushes. Decided against (D-11) — save toast is sufficient for v1.
- **Auto-detect sensors (promoted to implemented)** — superseded by D-17's area registry lookup. Implemented as fallback tier 2 in the priority chain.

</deferred>

---

*Phase: 3-WebSocket API & Frontend Panel*
*Context gathered: 2026-05-17*
