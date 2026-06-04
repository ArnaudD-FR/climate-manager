# Phase 10: Presence Mode UI - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 3 (2 modified + 1 new test)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/components/person-card.ts` | component | request-response | itself (surgical edit) | exact |
| `frontend/src/components/persons-tab.ts` | component | request-response | itself (surgical edit) | exact |
| `frontend/src/components/person-card.test.ts` | test | — | `frontend/src/components/week-parity.test.ts` | exact |

## Pattern Assignments

### `frontend/src/components/person-card.ts` (component, request-response)

**Analog:** itself — two surgical edits to existing methods and the `render()`
template.

**Existing `@property` declaration pattern** (lines 90–102):

```typescript
@property({ type: String }) personId!: string;
@property({ type: String }) personName!: string;
@property({ attribute: false }) config!: PersonConfig;
@property({ attribute: false }) roomChoices: RoomChoice[] = [];
@property({ attribute: false }) ws!: WsClient;
@property({ attribute: false }) panel!: ClimateManagerPanel;
@property({ attribute: false }) status: StatusPayload | null = null;

@state() _expanded = false;
@property({ type: Boolean }) autoExpand = false;
```

**New `@property` to add** — insert after `autoExpand` (line 102):

```typescript
@property({ type: Boolean }) hasDeviceTrackers = false;
```

Use `type: Boolean` (not `attribute: false`) so the parent can bind with
`.hasDeviceTrackers=${bool}` and Lit sets the JS property directly without
attribute reflection.

**Badge text rename** — `_getBadgeInfo()` lines 434–446:

```typescript
// BEFORE (line 442):
case PRESENCE_MODE_HA:
  return { cls: "ha", text: "HA home tracking" };

// AFTER:
case PRESENCE_MODE_HA:
  return { cls: "ha", text: "Live tracking" };
```

**Mode `<select>` — conditional option render** (lines 503–528):

```typescript
// BEFORE (lines 509–515): unconditional ha option
<option
  value=${PRESENCE_MODE_HA}
  ?selected=${currentMode === PRESENCE_MODE_HA}
>
  HA home tracking
</option>

// AFTER: conditional render + renamed label
${this.hasDeviceTrackers
  ? html`
      <option
        value=${PRESENCE_MODE_HA}
        ?selected=${currentMode === PRESENCE_MODE_HA}
      >
        Live tracking
      </option>`
  : ""}
```

Keep `?selected` binding on the conditionally rendered option — same pattern
as the always-rendered options (lines 504–508, 516–527).

**Schedule-hint paragraph — stuck-mode branch** (lines 530–537):

```typescript
// BEFORE (lines 530–537):
<p class="schedule-hint">
  ${currentMode === PRESENCE_MODE_FORCE_PRESENT
    ? "Always considered present, regardless of schedule."
    : currentMode === PRESENCE_MODE_FORCE_ABSENT
      ? "Always absent. Rooms are not heated for presence."
      : currentMode === PRESENCE_MODE_HA
        ? "Presence mirrors Home Assistant home/away tracking."
        : "Presence follows a weekly schedule."}
</p>

// AFTER: insert stuck-mode warning BEFORE the normal ha branch:
<p class="schedule-hint">
  ${currentMode === PRESENCE_MODE_FORCE_PRESENT
    ? "Always considered present, regardless of schedule."
    : currentMode === PRESENCE_MODE_FORCE_ABSENT
      ? "Always absent. Rooms are not heated for presence."
      : currentMode === PRESENCE_MODE_HA && !this.hasDeviceTrackers
        ? "Live tracking requires a device tracker linked to this person in HA."
        : currentMode === PRESENCE_MODE_HA
          ? "Presence mirrors Home Assistant home/away tracking."
          : "Presence follows a weekly schedule."}
</p>
```

The `.schedule-hint` CSS class is defined in `shared-styles.ts` lines 122–129
(12px font, secondary color, 6px top / 12px bottom margin). No new CSS needed.

---

### `frontend/src/components/persons-tab.ts` (component, request-response)

**Analog:** itself — one surgical addition to `render()` before the
`sortedIds.map()` call, plus one new prop on each `<climate-manager-person-card>`.

**Existing `hass.states` access pattern** (lines 91–94) — the same object
used to discover person IDs:

```typescript
const hassPersonIds = Object.keys(this.hass?.states ?? {}).filter((k) =>
  k.startsWith("person."),
);
const allPersonIds = [
  ...new Set([...hassPersonIds, ...Object.keys(persons)]),
];
```

`hass.states` is typed as
`Record<string, { state: string; attributes: Record<string, unknown> }>` —
see `frontend/src/types.ts` lines 138–141. The `device_trackers` attribute is
`unknown`, so it must be cast before calling `.length`.

**New `hasDeviceTrackersMap` computation** — insert after line 115
(`const roomChoices = this._getRoomChoices();`):

```typescript
// Compute hasDeviceTrackers per person from hass.states attributes.
// Treat absent attribute AND empty array both as false (D-02).
const hasDeviceTrackersMap = new Map<string, boolean>();
for (const personId of allPersonIds) {
  const trackers = this.hass?.states[personId]
    ?.attributes?.device_trackers as string[] | undefined;
  hasDeviceTrackersMap.set(personId, (trackers?.length ?? 0) > 0);
}
```

**Prop-forwarding pattern** (lines 127–136) — existing props forwarded with
dot-prefix property binding:

```typescript
<climate-manager-person-card
  .personId=${personId}
  .personName=${personName}
  .config=${personConfig}
  .roomChoices=${roomChoices}
  .ws=${this.ws}
  .panel=${this.panel}
  .status=${this.status}
  .autoExpand=${this.expandPersonId === personId}
></climate-manager-person-card>
```

**New prop to add** — append `.hasDeviceTrackers` in the same pattern:

```typescript
.hasDeviceTrackers=${hasDeviceTrackersMap.get(personId) ?? false}
```

The `?? false` fallback handles persons that exist in config but not in
`hass.states` (they were never discovered as HA entities).

---

### `frontend/src/components/person-card.test.ts` (test, new file)

**Analog:** `frontend/src/components/week-parity.test.ts` — exact structural
match (Node.js built-in test runner, `--experimental-strip-types`, no browser DOM).

**File header pattern** (week-parity.test.ts lines 1–16):

```typescript
// SPDX-License-Identifier: MIT
/**
 * Unit tests for [subject].
 *
 * Run: node --test --experimental-strip-types \
 *        src/components/person-card.test.ts
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { ... } from "./person-card.ts";
```

**Test case pattern** (week-parity.test.ts lines 18–21):

```typescript
test("description: expected outcome", () => {
  assert.equal(actualValue, expectedValue);
});
```

**What to test** — the five behaviors from the validation architecture:

| Req | Test description | Assertion |
|---|---|---|
| UI-02 | `_getBadgeInfo()` returns "Live tracking" when mode is "ha" | `assert.equal(badge.text, "Live tracking")` |
| UI-02 | option label text is "Live tracking" (not "HA home tracking") | string match on rendered template |
| UI-01 | "Live tracking" option absent when `hasDeviceTrackers=false` | option not in select |
| UI-01 | "Live tracking" option present when `hasDeviceTrackers=true` | option in select |
| UI-01 | stuck-mode warning renders when `mode="ha" && !hasDeviceTrackers` | p.schedule-hint text |

Because `_getBadgeInfo()` is a private method, prefer testing it by
instantiating the class and reading the badge info indirectly, or by
extracting the logic into a pure function (same approach as `week-parity.ts`
exporting `getISOWeekNumber` / `getWeekParity` for testability without Lit).

**Invocation command** (mirrors week-parity.test.ts header and RESEARCH.md):

```bash
node --test --experimental-strip-types \
  frontend/src/components/person-card.test.ts
```

---

## Shared Patterns

### Native `<select>` (not `ha-select`)

**Source:** `frontend/src/components/person-card.ts` lines 502–528,
`frontend/src/shared-styles.ts` lines 98–119

All dropdowns in this codebase use native `<select class="mode-select">`.
`ha-select` is broken in HA 2026.x (project memory). Do not regress.

```typescript
<div class="select-wrapper">
  <select class="mode-select" @change=${this._onModeChange}>
    <option value="..." ?selected=${...}>...</option>
  </select>
</div>
```

### Conditional Lit template rendering

**Source:** `frontend/src/components/person-card.ts` lines 570–588 (unassigned
rooms search-picker) and lines 592–668 (schedule section)

```typescript
${condition ? html`<element>...</element>` : ""}
```

Use empty string `""` (not `nothing`) for "render nothing" — consistent with
existing conditional blocks in this file.

### Auto-save on change — no Save button

**Source:** `frontend/src/components/person-card.ts` lines 308–329
(`_onModeChange` handler)

```typescript
private async _onModeChange(e: Event) {
  const newMode = (e.target as HTMLSelectElement).value;
  if (!newMode) return;
  try {
    await this.ws.setPersonConfig(this.personId, { mode: newMode });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

Phase 9 D-12: auto-save on change, no Save button. This pattern applies to
all mode changes. D-05 explicitly forbids a silent `setPersonConfig` call on
render for the stuck-mode case — the handler only fires on explicit user input.

### `.schedule-hint` inline warning

**Source:** `frontend/src/shared-styles.ts` lines 122–129

```typescript
export const scheduleHintStyles = css`
  .schedule-hint {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin: 6px 0 12px;
    line-height: 1.5;
  }
`;
```

Already imported in `PersonCard.static styles` (line 168). Use `<p
class="schedule-hint">` for the stuck-mode warning — no new CSS class needed.

### SPDX license header

**Source:** all `.ts` files in `frontend/src/`

```typescript
// SPDX-License-Identifier: MIT
```

Every TypeScript file starts with this comment. Required by project convention.

## No Analog Found

None — all three files have direct analogs in the codebase.

## Metadata

**Analog search scope:** `frontend/src/components/`, `frontend/src/`
**Files read:** 5 (person-card.ts, persons-tab.ts, shared-styles.ts,
types.ts, week-parity.test.ts)
**Pattern extraction date:** 2026-05-31
