# Phase 6: Zone & Room Assignment UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 06-Zone & Room Assignment UI
**Areas discussed:** Zone creation UX, Room assignment in zone tab, Zone picker on room card, Inline zone name editing, HA presence mode label (folded todo)

---

## Zone Creation UX

### Where does the create button live?

| Option | Description | Selected |
|--------|-------------|----------|
| + button in the tab bar | After last custom zone tab, before Rooms | ✓ |
| Button at the top of the Default Zone tab | Inside Default Zone tab content | |
| Button above the tab bar | Between panel header and tab bar | |

**User's choice:** + button in the tab bar — "choice 1 but in this case zones should be the latest tabs"
**Notes:** Custom zones appear after Default Zone and before the + button. Tab order confirmed: Global Settings | Default Zone | [custom zones] | + | Rooms | Persons.

### What happens on + click?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline prompt in tab bar | + transforms into text input in tab bar | |
| Create immediately with default name | WS call fires, new tab appears and becomes active | ✓ |

**User's choice:** Create immediately with default name
**Notes:** New tab becomes active; name field is focused for immediate renaming.

### Default name format

| Option | Description | Selected |
|--------|-------------|----------|
| "Zone N" (N = count + 1) | Backend computes N from existing zone count | ✓ |
| "New Zone" | Fixed label regardless of count | |

**User's choice:** "Zone N" where N = count of existing zones + 1

---

## Room Assignment in Zone Tab

### Assignment interaction pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Search-picker + chips | Reuses search-picker.ts; same as person association | ✓ |
| Checklist of all rooms | Checkbox list, scrollable | |

**User's choice:** Search-picker + chips

### Where does a removed room go?

| Option | Description | Selected |
|--------|-------------|----------|
| Back to Default Zone | Remove zone_id from room config (sparse model) | ✓ |
| Prompt user to pick a zone | Mini picker after removal | |

**User's choice:** Back to Default Zone

### Layout: where in the zone tab?

| Option | Description | Selected |
|--------|-------------|----------|
| Below the time-bar | Schedule config first, assignment at bottom | ✓ |
| Above the time-bar | Assignment more prominent | |
| You decide | Claude picks layout | |

**User's choice:** Below the time-bar

---

## Zone Picker on Room Card

### Picker style

| Option | Description | Selected |
|--------|-------------|----------|
| Native `<select>` dropdown | Consistent with mode picker; auto-save on change | ✓ |
| Zone badge chip + click-to-change | Visual badge in header, click opens picker | |

**User's choice:** Native `<select>` dropdown

### Picker placement in room card

| Option | Description | Selected |
|--------|-------------|----------|
| Below mode picker, above persons | Keeps config fields together | ✓ |
| Above mode picker (top of expanded) | Zone as primary field | |
| You decide | Claude picks placement | |

**User's choice:** Below mode picker, above persons section

### Zone badge in header vs. expanded only

| Option | Description | Selected |
|--------|-------------|----------|
| In collapsed header (always visible) | Small pill next to room name | ✓ |
| Only in expanded content | Cleaner header, hidden until expanded | |

**User's choice:** In collapsed header — always visible

---

## Inline Zone Name Editing

### Edit interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Click-to-edit text | Text → click → input → blur/Enter saves | ✓ |
| Always-visible input field | Input always rendered with label | |

**User's choice:** Click-to-edit

### Tab label update timing

| Option | Description | Selected |
|--------|-------------|----------|
| Updates on save (blur/Enter) | After WS success | ✓ |
| Updates live while typing | Real-time tab label update | |

**User's choice:** Updates on save (after WS round-trip confirms)

### Default Zone name editable?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — same click-to-edit pattern | Uses rename_zone WS | ✓ |
| No — fixed static text | Simpler, inconsistent | |

**User's choice:** Yes — same pattern for Default Zone and custom zones

---

## HA Presence Mode Label (Folded Todo)

**Todo:** "Rename 'ha' person presence mode to a clearer label in the UI"
**Decision to fold:** Yes

### Label selection (first pass)

| Option | Description | Selected |
|--------|-------------|----------|
| "HA presence" | Short, unambiguous | |
| "Real-time" | Emphasizes live tracking | |
| "Auto (HA)" | Signals automatic, HA-driven | |

**User's choice (free text):** "Find something more Person at home with home assistant"

### Label selection (second pass)

| Option | Description | Selected |
|--------|-------------|----------|
| "HA home tracking" | Combines HA + home + tracking | ✓ |
| "Live tracking" | Real-time, without HA acronym | |
| "Person entity" | Technical, precise | |

**User's choice:** "HA home tracking"
**Notes:** Display-only change. Backend value "ha" unchanged. Affects person-card.ts (badge + select option) and persons-tab.ts (badge text).

---

## Claude's Discretion

- **Tab identity system:** `_activeTab` broadened to `string`. Format: `"zone_default"` / `"zone_<uuid>"` for zones. localStorage fallback to `"global"` if stored zone ID no longer exists.
- **Zone tab component architecture:** Single `zone-tab.ts` component with `isDefault` boolean prop. When `true`: hides delete button, uses `global_mode` / `global_time_program` as props.
- **Delete confirmation:** Inline row (no ha-dialog) — replace button with confirm/cancel row on first click.

## Deferred Ideas

- Adaptive pre-heat (v2)
- Boiler demand control (v2)
- Per-zone boiler declaration (v2)
- Even/odd week presence scheduling (v2)
- "Multi-zone heating" todo: already covered by this milestone — no separate action needed.
