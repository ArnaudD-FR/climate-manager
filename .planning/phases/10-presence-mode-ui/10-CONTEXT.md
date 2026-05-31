# Phase 10: Presence Mode UI - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Two targeted UI changes to the person card in the Persons tab:

1. Rename every instance of the "HA" / "HA home tracking" label to "Live
   tracking" (internal `mode: "ha"` key is unchanged in config storage —
   UI-only relabeling, no migration needed).
2. Conditionally hide the "Live tracking" option from the presence mode picker
   when the HA `person.*` entity has no linked device trackers
   (`attributes.device_trackers` absent or empty array).

**In scope:**
- `frontend/src/components/person-card.ts` — label rename + conditional
  option rendering + stuck-mode warning
- `frontend/src/components/persons-tab.ts` — compute `hasDeviceTrackers`
  boolean per person and pass to PersonCard

**Out of scope:**
- Backend changes (no new WS commands, no status payload fields)
- Any change to the internal `"ha"` mode value stored in config
- Other presence modes (scheduled, force_present, force_absent)
- Auto-migrating persons currently set to "ha" without device trackers

</domain>

<decisions>
## Implementation Decisions

### Label Rename (UI-02)

- **D-01:** Every UI surface that currently shows "HA", "HA home tracking", or
  similar replaces with **"Live tracking"**. Affected surfaces:
  - `<option>` label in the mode `<select>` (person-card.ts line ~515)
  - Badge text in `_getBadgeInfo()` (person-card.ts line ~442)
  - Hint paragraph below the select (person-card.ts line ~536)
  - The internal constant `PRESENCE_MODE_HA = "ha"` stays as-is (config key,
    not a display string).

### Hide Mechanism (UI-01)

- **D-02:** Frontend-only check — no backend changes. `PersonsTab` computes a
  `hasDeviceTrackers: boolean` per person by reading
  `hass.states[personId]?.attributes?.device_trackers`. The attribute is an
  array; the check is `(arr?.length ?? 0) > 0`.
- **D-03:** `PersonsTab` passes `hasDeviceTrackers` as a new boolean prop to
  `<climate-manager-person-card>`. `PersonCard` declares
  `@property({ type: Boolean }) hasDeviceTrackers = false;`.
- **D-04:** When `hasDeviceTrackers` is `false` (or the person entity is
  absent from `hass.states`), the "Live tracking" `<option>` is not rendered
  in the select. The three other options remain (Scheduled, Force Present,
  Force Absent).

### Stuck-Mode Edge Case

- **D-05:** If a person currently has `mode: "ha"` in config but
  `hasDeviceTrackers` is `false`, `PersonCard` renders a small inline warning
  below the select rather than auto-migrating or staying silent:
  ```
  Live tracking requires a device tracker linked to this person in HA.
  ```
  The user must manually switch to another mode; no automatic `setPersonConfig`
  call fires on render.

### Folded Todos

- **Rename "ha" presence mode to a clearer label (2026-05-27):** Directly maps
  to UI-02. Todo recommended "Live tracking" (or "HA person entity"). Decision:
  "Live tracking" as per requirements.
- **Hide HA presence mode when person has no tracked device (2026-05-30):**
  Directly maps to UI-01. Todo proposed two approaches (frontend / backend
  flag); decision: frontend-only (D-02).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Presence Mode UI — UI-01, UI-02 (full
  acceptance criteria)
- `.planning/ROADMAP.md` §Phase 10 — success criteria and phase boundaries

### Key Source Files
- `frontend/src/components/person-card.ts` — the file receiving most changes;
  read fully before editing (mode constants, badge logic, select render, hint
  paragraph)
- `frontend/src/components/persons-tab.ts` — where `hasDeviceTrackers` is
  computed from `hass.states` and passed to PersonCard
- `frontend/src/types.ts` §Hass — `hass.states` shape, `attributes` type

### Established Patterns (from prior phases)
- `frontend/src/components/person-card.ts` §selectStyles — existing native
  `<select>` usage (not `ha-select` — broken in HA 2026.x)
- `frontend/src/shared-styles.ts` — shared CSS class definitions used by
  PersonCard
- Phase 9 CONTEXT.md D-12: auto-save on change, no Save button

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `person-card.ts:_getBadgeInfo()` — badge label switch statement;
  `PRESENCE_MODE_HA` case returns `{ cls: "ha", text: "HA home tracking" }` —
  update text to "Live tracking"
- `person-card.ts` lines 503–529 — mode `<select>` with 4 `<option>` elements;
  the `ha` option is rendered unconditionally — add `?hasDeviceTrackers` guard
- `persons-tab.ts` — already reads `hass.states` for person entity discovery
  (lines 91–94); extend to compute `hasDeviceTrackers` map

### Established Patterns
- **Native `<select>`:** All dropdowns use native `<select>` (not `ha-select`).
  The conditional hide is implemented by conditionally rendering the `<option>`
  element, not by disabling it.
- **Prop forwarding:** `PersonsTab` already passes `.ws`, `.panel`, `.status`
  to each PersonCard; add `.hasDeviceTrackers=${boolean}` in the same pattern.
- **Inline hint paragraph:** The `<p class="schedule-hint">` below the select
  (line ~530) already varies by mode — add the warning text for the stuck-mode
  case when `mode === 'ha' && !hasDeviceTrackers`.

### Integration Points
- `persons-tab.ts:render()` — add `hasDeviceTrackers` computation before the
  `sortedIds.map(...)` call; thread it into each `<climate-manager-person-card>`
  instantiation.
- `person-card.ts:PersonCard` class — add `hasDeviceTrackers` prop declaration;
  update `_getBadgeInfo()`, the `<select>` render, and the hint paragraph.

</code_context>

<specifics>
## Specific Ideas

- "Live tracking" is the chosen label — not "HA tracker", "HA person entity",
  or "Live detection". Exact string to use in all UI surfaces.
- Warning message for stuck mode: "Live tracking requires a device tracker
  linked to this person in HA." — displayed as inline text (same `.schedule-hint`
  class), not a toast or modal.
- The `hass.states[personId]?.attributes?.device_trackers` check: treat absent
  attribute AND empty array both as "no device trackers" (`length === 0` or
  undefined).

</specifics>

<deferred>
## Deferred Ideas

- **Backend `has_device_tracker` flag in status payload** — reviewed but not
  folded. Frontend-only approach is sufficient; backend flag would be cleaner
  for the component but adds complexity without clear benefit at this phase.
- **Auto-migrate persons stuck on "ha" mode** — discussed; decided against.
  User must switch manually. Auto-migration on render would fire a WS call
  silently, which is surprising behavior.

### Reviewed Todos (not folded)
- **Even/odd week presence scheduling (score 0.6)** — already shipped in
  Phase 7–8; not relevant to Phase 10 scope.
- **Multi-language support (score 0.5)** — deferred to v2 in REQUIREMENTS.md.
- Other todos with score < 0.4 — not relevant to UI label/hide changes.

</deferred>

---

*Phase: 10-presence-mode-ui*
*Context gathered: 2026-05-31*
