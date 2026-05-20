# Phase 3: WebSocket API & Frontend Panel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17 (updated 2026-05-20, 2026-05-20)
**Phase:** 3-WebSocket API & Frontend Panel
**Areas discussed:** Time program editor, Save model, Panel navigation, Panel status display, Rooms ordering (2026-05-20), Room card always-visible status (2026-05-20)

---

## Time Program Editor

| Option | Description | Selected |
|--------|-------------|----------|
| Weekday groups (current backend) | Groups of days sharing a period list — flexible, backend already implemented | |
| Per-day schema (Tado-style) | Each day independent, simple dict lookup, familiar UX | ✓ |

**User's choice:** Per-day schema
**Notes:** User referenced Tado app as the UX reference. Per-day is simpler to develop and maintain; users can see the planning clearly. Requires a gap-closure refactor of Phase 2 backend before Phase 3 begins.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Visual timeline grid (full week) | 7-column × 24-hour grid, drag to resize | |
| Period list table | Table of start-time + mode rows per day | |
| Visual 24h bar per day (all stacked) | Colored bars, all 7 days visible at once | ✓ |

**User's choice:** Visual 24h bar, all 7 stacked
**Notes:** User confirmed "visual bar with copy button on the right." Added clarification that the copy button should be on the right of the bar.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Click bar to split + pick mode | Click splits at that time, popup for mode | ✓ |
| Right-click context menu | Right-click opens Split/Change/Delete menu | |

**User's choice:** Click bar to split
**Notes:** User added "when dragging borders, the exact time should be visible via a kind of popup." Confirmed "interactive bar."

---

| Option | Description | Selected |
|--------|-------------|----------|
| Click block → popup with Delete | Popup shows time range, mode, [Change mode], [Delete] | ✓ |
| Drag border to zero width | Drag away to delete | |

**User's choice:** Click block → popup with Delete option

---

| Option | Description | Selected |
|--------|-------------|----------|
| Copy to ▼ dropdown | Single button with dropdown to select target days | |
| [Copy] + [Paste] per row | Clipboard model: one click copy, one click paste per target | ✓ |

**User's choice:** [Copy] and [Paste] buttons
**Notes:** "less interaction for user with the same result." Copy stores in panel clipboard state; Paste applies to target day.

---

**Period colors (free text from user):**
- Frost protection: deep blue
- Reduced: light blue
- Normal: orange
- Comfort: red

---

## Save Model

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit Save button per section | Save button per section, supports cancel | |
| Auto-save on change | Every field change fires WebSocket immediately | ✓ |
| Save button for time program only | Simple fields auto-save, time programs need explicit save | |

**User's choice:** Auto-save on change

---

| Option | Description | Selected |
|--------|-------------|----------|
| On interaction end | Save on mouse-up, popup close, paste | ✓ |
| Immediately on every change | Save mid-drag (floods WebSocket) | |

**User's choice:** On interaction end (for time program bar)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Toast notification | Brief snackbar, fades on success | ✓ |
| Inline error near field | Stays visible, more precise | |
| Silent retry only | No user notification | |

**User's choice:** Toast notification

---

| Option | Description | Selected |
|--------|-------------|----------|
| No "Applied" feedback | Save toast is sufficient | ✓ |
| Show "Applied" after coordinator push | Requires WebSocket event back to panel | |

**User's choice:** No "Applied" feedback — "✓ Saved" toast is sufficient

---

## Panel Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Top tabs | Global Settings / Rooms / Persons tabs | ✓ |
| Single scrollable page | All sections on one page | |
| Left sidebar navigation | Side nav panel | |

**User's choice:** Top tabs

---

| Option | Description | Selected |
|--------|-------------|----------|
| Expandable cards | Cards expand inline, toggle for override | ✓ |
| Flat list with edit links | List + navigate to room edit page | |

**User's choice:** Expandable cards (for both Rooms and Persons tabs)
**Notes:** User added: "when a room or a person has been configured it should be expanded by default." Confirmed rooms with custom program and persons with non-default settings are expanded by default. This aligns with Phase 1 D-17/D-18 ordering rules.

---

## Panel Status Display

| Option | Description | Selected |
|--------|-------------|----------|
| Config only — no live data | No current temperatures or availability | |
| Minimal live hints | TRV availability indicator only | |
| Full live status | Temperature, active period, TRV availability | |
| Custom (user-specified) | Current temp + humidity + active period + present persons | ✓ |

**User's choice:** Show current room temperature + humidity + active period. Show present persons on Global Settings tab only.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Nice to have — show if available | Best-effort humidity sensor discovery | |
| Required — add humidity discovery | Mandatory sensor per room | |
| Skip humidity | Out of scope | |
| User-configurable sensors | User defines temp + humidity sensor per room | ✓ |

**User's choice:** User can define optional `temperature_sensor` and `humidity_sensor` entity IDs per room. Panel displays these if defined; falls back to TRV's `current_temperature` for temperature, hides humidity if no sensor defined.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Banner on Rooms tab | Present persons above room cards | |
| Badge on each person card only | Live dot per person in Persons tab | |
| Both | Banner + badge | |
| Global Settings tab only | Present persons shown only in Global status section | ✓ |

**User's choice:** Persons status on Global Settings tab only (in the Current Status section)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Status section at top, config below | Read-only status strip + config controls below | ✓ |
| Config only on Global tab | No status section | |

**User's choice:** Status section at top (current mode, active period, present persons), configuration section below.

---

## Claude's Discretion

- WebSocket command granularity (per-field vs. section-level saves)
- Frontend build integration into Makefile
- `async_register_panel` exact signature (verify against HA source)
- Whether to bundle Lit into `panel.js` or use HA's Lit instance (default: bundle)

## Deferred Ideas

- TRV availability indicator (reachable/unreachable dot per entity) — v2
- Entity picker for sensor fields (searchable dropdown) — v2 UX improvement
- "Applied" confirmation after coordinator push — decided against for v1
- Auto-detect humidity sensors by area_id — v2 quality-of-life feature

---

## Rooms Ordering (2026-05-20)

### D-14 Ordering Rule

| Option | Description | Selected |
|--------|-------------|----------|
| Replace D-14 entirely | Order purely by floor → room name; custom-program rooms expand but don't sort first | ✓ |
| Floor then custom-program within floor | Within each floor, custom-program rooms first | |
| Keep D-14, floor as secondary sort | Custom-program first, then floor within each group | |

**User's choice:** Replace D-14 entirely
**Notes:** Custom-program rooms still expand by default — only their sort position changes. The HA climate panel (ha.local/climate) was the reference.

---

### Floorless Rooms

| Option | Description | Selected |
|--------|-------------|----------|
| At the end, unlabeled | After all floored rooms, alphabetical, no header | ✓ |
| At the end, in an 'Other' group | Same position, with explicit 'Other' section header | |
| At the top, alphabetically | Before all floored rooms | |

**User's choice:** At the end, unlabeled

---

### Floor Section Headers

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, show floor name headers | Section header per floor (e.g. "Ground floor") | ✓ |
| No headers — just ordered cards | Ordered correctly but no visual separator | |

**User's choice:** Yes, show floor name headers

---

### Claude's Discretion (Rooms Ordering)

- Data source: `hass.areas` + `hass.floors` (frontend only — no backend changes)
- Floor level ordering: ascending by `floor.level` integer

---

## Room Card Always-Visible Status (2026-05-20)

### Layout
- **Options presented:** Second line in header (compact row below name+badge) / Right side of header row (inline with chevron)
- **Decision:** Second line in the header — compact row below name + badge, always visible whether expanded or not

### Expanded card duplication
- **Options presented:** Remove status row from expanded content / Keep it (redundant)
- **Decision:** Remove the `.status-row` from expanded `.card-content` — header is the single source

### Missing data
- **Options presented:** Hide silently / Show "—" placeholder
- **Decision:** Show "—" placeholder — consistent layout, all 3 slots always present
