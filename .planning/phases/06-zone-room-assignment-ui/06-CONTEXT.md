# Phase 6: Zone & Room Assignment UI - Context

**Gathered:** 2026-05-28 **Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the full zone management UI in the Lovelace panel: dynamic zone tabs,
per-zone configuration (inline name editing, mode picker, time-bar, assigned
rooms), room zone assignment from both the zone tab and room cards, and zone
badges on every room card header.

**In scope:**

- Tab bar restructured: Global Settings | Default Zone | [custom zone tabs] | +
  | Rooms | Persons
- Dynamic zone tabs: appear immediately on create, disappear on delete
- Zone creation: `+` button in tab bar → `create_zone` WS call → new tab becomes
  active (name focused)
- Per-zone tab: click-to-edit name, mode picker, time-bar, assigned rooms
  (search-picker + chips)
- Room assignment in zone tab: search-picker pattern (reuses `search-picker.ts`)
- Room card: zone badge in collapsed header + zone `<select>` picker in expanded
  content
- Rooms tab: zone badge + zone `<select>` on each room card (ASSIGN-03, UI-06)
- `ha` presence mode label renamed to "HA home tracking" throughout the panel

**Out of scope:**

- Backend zone evaluation (Phase 5)
- Zone WebSocket commands (Phase 5)
- Per-zone temperature setpoints (v2)
- Zone priority ordering (v2)

</domain>

<decisions>
## Implementation Decisions

### Zone Creation (UI-03)

- **D-01:** `+` button lives in the tab bar, positioned after the last custom
  zone tab and before the Rooms tab. Tab order: Global Settings | Default Zone |
  [custom zones] | **+** | Rooms | Persons.
- **D-02:** Clicking `+` fires `create_zone` immediately with a default name
  computed by the backend as "Zone N" (N = total custom zones count + 1 at
  creation time). No name-input prompt before creation.
- **D-03:** After `create_zone` resolves, the new zone tab is rendered and
  becomes active. The name field within the tab is focused immediately so the
  user can rename without a second click.

### Zone Tab Layout (UI-04)

- **D-04:** Tab layout top-to-bottom: zone name (click-to-edit) → mode picker →
  weekly time-bar → Assigned Rooms section. Scheduling config comes first; room
  assignment is at the bottom.
- **D-05:** Delete button (custom zones only, per UI-05): positioned at the
  top-right of the zone tab content area, visible above the name. Confirmation
  is an inline row that replaces the button on first click ("Delete zone?
  [Cancel] [Confirm]") — no ha-dialog (unavailable in HA 2026.x).

### Zone Name Editing (UI-04)

- **D-06:** Zone name uses click-to-edit: displayed as styled text → click →
  transforms into `<input>` → blur or Enter saves via `rename_zone` WS → Escape
  cancels. Tab label in the tab bar updates after the WS round-trip confirms
  success.
- **D-07:** Default Zone name is editable via the same click-to-edit pattern,
  using `rename_zone` (which updates `default_zone_name` on the backend). No
  difference in editing UX between Default Zone and custom zones.

### Room Assignment in Zone Tab (ASSIGN-01, UI-04)

- **D-08:** Assigned rooms are shown as chips (room name + ×). Clicking ×
  removes the room from the zone and sends it back to the Default Zone
  (`set_room_config` with `zone_id` absent — sparse model).
- **D-09:** Adding rooms: a search-picker (reuses `search-picker.ts`) shows
  rooms not yet assigned to this zone. Selecting a room fires `set_room_config`
  with `zone_id` set to this zone's UUID.
- **D-10:** The search-picker for rooms should exclude rooms already assigned to
  this zone, and filter the searchable list to only unassigned rooms (or rooms
  in other zones — all valid assignment targets).

### Zone Badge & Picker on Room Card (ASSIGN-02, ASSIGN-03, UI-06)

- **D-11:** Zone badge is displayed in the **collapsed card header** row, always
  visible — small pill next to the room name, similar to the program badge.
  Shows the zone's display name (Default Zone name if no custom zone assigned).
- **D-12:** Zone assignment picker: native `<select>` dropdown in the expanded
  card content, placed **below the mode picker and above the persons section**.
  Options: Default Zone name + all custom zone names. Auto-save on change via
  `set_room_config`.

### HA Presence Mode Label (folded todo)

- **D-13:** The `ha` presence mode (currently labeled "HA") is renamed to **"HA
  home tracking"** everywhere it appears in the panel: mode badge, `<select>`
  option in the person card mode selector. Backend value `"ha"` is unchanged —
  this is a display-only label change.

### Claude's Discretion

- Tab identity for `_activeTab` in main.ts: extend to support dynamic zone IDs
  (e.g., `"zone_default"` and `"zone_<uuid>"`). localStorage restore should fall
  back to "global" if the stored zone ID no longer exists (deleted zone).
- Zone tab component architecture: one shared `zone-tab.ts` component with an
  `isDefault` boolean prop controls whether the delete button renders. Avoids
  duplicating the time-bar + mode picker logic.
- `_activeTab` type: change from union of literals to `string` (or a broader
  type) to accommodate dynamic zone UUIDs.

### Folded Todos

- **"Rename 'ha' person presence mode to a clearer label in the UI"**
  (2026-05-27): Folded into Phase 6 as D-13. Pure label rename — no backend
  changes. Label: "HA home tracking".

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Panel Components (all in `frontend/src/`)

- `frontend/src/main.ts` — Root panel: CSS button tab-bar pattern, `_activeTab`
  state, `_setTab()`, `reloadConfig()`, `patchConfig()`, `showToast()`. Zone
  tabs extend this with dynamic tab rendering.
- `frontend/src/components/room-card.ts` — Room card: chip pattern (persons
  section), `search-picker.ts` usage via `@picked` event, native `<select>` for
  mode picker, expand/collapse, `ha-card` pattern. Zone badge and zone picker go
  here.
- `frontend/src/components/rooms-tab.ts` — Renders room cards; floor grouping
  pattern. Zone badges appear inside each room card — no structural changes to
  rooms-tab needed.
- `frontend/src/components/global-settings-tab.ts` — Time-bar integration
  pattern: `programToDays()` / `dayIndexToKey()` helpers (exported, reusable),
  `_cachedDays` memoization pattern. Zone tab must replicate this memoization.
- `frontend/src/components/person-card.ts` — `PRESENCE_MODE_HA = "ha"` constant
  and `"HA"` label at lines 28 and 411. D-13 renames these display strings.
- `frontend/src/components/persons-tab.ts` — `PRESENCE_MODE_HA` badge label at
  line 373 (`text: "HA"`). D-13 update target.
- `frontend/src/components/search-picker.ts` — Searchable dropdown used for
  person association. Reuse as-is for room assignment in zone tabs.
- `frontend/src/ws-client.ts` — WS client: no zone methods yet. Needs:
  `createZone`, `deleteZone`, `renameZone`, `setZoneMode`, `setZoneTimeProgram`,
  `resetZoneTimeProgram`, and `setRoomConfig` (already exists) for zone_id
  updates.
- `frontend/src/types.ts` — `ZoneConfig`, `RoomConfig.zone_id`,
  `ClimateConfig.zones`, `ClimateConfig.default_zone_name` already defined
  (Phase 4). No new types needed.

### WebSocket API (backend)

- `custom_components/climate_manager/websocket.py` — 6 zone commands registered
  in Phase 5: `create_zone`, `delete_zone`, `rename_zone`, `set_zone_mode`,
  `set_zone_time_program`, `reset_zone_time_program`. Frontend calls these
  directly.

### Requirements

- `.planning/REQUIREMENTS.md` — ASSIGN-01, ASSIGN-02, ASSIGN-03 (room
  assignment); UI-01 through UI-06 (panel UI redesign). Read carefully — all 9
  requirements target this phase.
- `.planning/ROADMAP.md` — Phase 6 success criteria (5 behavioural scenarios).

### Prior Phase Context

- `.planning/phases/05-zone-crud-evaluation-engine/05-CONTEXT.md` — D-03
  (create_zone returns full zone config), D-04 (command signatures), D-05
  (rename_zone default zone routing via zone_id="default" sentinel).
- `.planning/phases/04-zone-data-model-storage/04-CONTEXT.md` — D-01 (no storage
  entry for Default Zone), D-02 (Default Zone mode/program =
  global_mode/global_time_program), D-06 (absent zone_id = Default Zone member),
  D-07 (UUID zone keys).

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `search-picker.ts` — accepts `.items` array of
  `{id, label, secondary?, icon?}`, emits `@picked` with `{detail: {id}}`. Used
  verbatim for room assignment (rooms as items, room name as label).
- `programToDays(program)` / `dayIndexToKey(index)` — exported from
  `global-settings-tab.ts`. Zone tab uses these to feed the time-bar. Must
  replicate the `_lastTimeProgram` / `_cachedDays` memoization pattern to
  prevent time-bar drag flicker on status re-renders.
- `room-card.ts` chip pattern (`.chips`, `.chip`, `.chip-remove`) — copy CSS and
  render pattern for assigned-rooms chips in the zone tab.
- `WsClient` class in `ws-client.ts` — add 6 zone methods following the existing
  `sendMessagePromise` pattern. `setRoomConfig` already handles `zone_id` (it's
  a `Partial<RoomConfig>`).

### Established Patterns

- **CSS button tabs (HA 2026.x):** `main.ts` uses `.tab-bar` + `.tab-btn` +
  `.tab-btn.active` — the only working tab pattern. No `ha-tabs` or `paper-tab`.
- **Native `<select>` for dropdowns (HA 2026.x):** `room-card.ts` `.mode-select`
  — copy class and styling for zone picker and zone mode picker.
- **Auto-save on change:** All pickers fire WS call immediately on `@change`
  then call `panel.reloadConfig()`. Zone pickers follow the same pattern.
- **Chip association pattern:** `room-card.ts` persons section — chips array +
  chip-x remove + search-picker add. Exact same pattern for assigned rooms in
  zone tabs.
- **Write-then-reload:** All writes call WS → `panel.reloadConfig()` →
  `panel.showToast()`. Zone writes follow identically.
- **Memoized days array:** `global-settings-tab.ts` `_lastProgram` /
  `_cachedDays` — mandatory for any component that passes days to
  `<climate-manager-time-bar>`.

### Integration Points

- `main.ts` `render()` and `_renderTabContent()` — must be extended to render
  dynamic zone tabs from `_config.zones` + the Default Zone. `_activeTab` type
  broadened to `string`.
- `main.ts` tab-bar — `+` button after the last zone tab, before Rooms. On
  click: `ws.createZone(defaultName)` → `reloadConfig()` → `_setTab(newZoneId)`.
- `room-card.ts` header row — add zone badge pill and (in expanded content) zone
  `<select>`.
- `ws-client.ts` — add `createZone(name)`, `deleteZone(zoneId)`,
  `renameZone(zoneId, name)`, `setZoneMode(zoneId, mode)`,
  `setZoneTimeProgram(zoneId, program)`, `resetZoneTimeProgram(zoneId, target)`.
- `person-card.ts` line 28 (`PRESENCE_MODE_HA`) and line 411 (option label) +
  `persons-tab.ts` line 373 (badge text): update display string to "HA home
  tracking".

</code_context>

<specifics>
## Specific Ideas

- `+` button styling: same `.tab-btn` class with a `+` symbol only (no text
  label). On hover: shows "Add zone" tooltip via `title` attribute.
- Zone tab `isDefault` prop:
  `<climate-manager-zone-tab .isDefault=${zoneId === "default"}>` — when `true`,
  hide delete button, use `global_mode` / `global_time_program` as the
  mode/program props.
- localStorage tab ID format: `"zone_default"` for Default Zone, `"zone_<uuid>"`
  for custom zones. On app init, if stored tab is `"zone_<uuid>"` and that UUID
  is not in `_config.zones`, fall back to `"global"`.
- Default zone name (`_config.default_zone_name`) is displayed as the zone badge
  for rooms with no `zone_id`.
- `create_zone` WS call payload:
  `{type: "climate_manager/create_zone", name: "Zone N"}`. The `N` is computed
  client-side as `Object.keys(this._config!.zones).length + 1`.
- Delete confirmation inline row (no dialog): on delete click, replace button
  with
  `<span>Delete zone?</span> <button>Cancel</button> <button class="danger">Confirm</button>`.
  On Confirm: `deleteZone(zoneId)` → `reloadConfig()` →
  `_setTab("zone_default")`.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)

- **"Adaptive pre-heat with dynamic room inertia learning"** (score 0.6) — v2
  feature, out of scope.
- **"Boiler demand control"** (score 0.6) — v2 feature, requires boiler entity
  concept.
- **"Per-zone boiler declaration"** (score 0.4) — v2 feature, out of scope.
- **"Even/odd week presence scheduling"** (score 0.4) — v2 feature, out of
  scope.
- **"Multi-zone heating: Define multiple heating zones"** (score 0.6) — seeded
  this milestone; already fully in scope across Phases 4-6. No separate action
  needed.

</deferred>

---

_Phase: 6-Zone & Room Assignment UI_ _Context gathered: 2026-05-28_
