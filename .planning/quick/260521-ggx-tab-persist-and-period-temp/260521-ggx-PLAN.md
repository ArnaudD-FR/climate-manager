---
quick_id: 260521-ggx
slug: tab-persist-and-period-temp
description:
  "Tab persistence on refresh + period temperature in room card header"
date: 2026-05-21
must_haves:
  truths:
    - Refreshing the panel restores the previously active tab
      (global/rooms/persons)
    - localStorage key "climate-manager-tab" stores the active tab
    - Invalid/missing localStorage values fall back to "global"
    - Room card header shows period display name + temperature (e.g. "Normal ·
      20°C")
    - Period display name uses PERIOD_DISPLAY_NAMES from types.ts
    - Period temperature comes from panelConfig.period_temperatures
  artifacts:
    - frontend/src/main.ts
    - frontend/src/components/room-card.ts
---

# Quick Task 260521-ggx: Tab Persistence + Period Temperature

## Goal

Two UX improvements:

1. Active tab survives a page refresh — stored in localStorage
2. Room card header period chip shows display name + temperature (e.g. "Normal ·
   20°C")

## Task 1: Tab persistence on refresh

**File:** `frontend/src/main.ts`

**Current:** `@state() private _activeTab = "global";` — lost on every refresh

**Change:**

- Initialize `_activeTab` from `localStorage.getItem("climate-manager-tab")`,
  validating against `["global", "rooms", "persons"]`, falling back to
  `"global"` if missing/invalid
- In `_setTab(tab)`, add `localStorage.setItem("climate-manager-tab", tab)`
  after setting `this._activeTab`

```typescript
// Initializer (replace the existing @state line):
@state() private _activeTab: string = (() => {
  const t = localStorage.getItem("climate-manager-tab");
  return ["global", "rooms", "persons"].includes(t ?? "") ? t! : "global";
})();

// _setTab (add localStorage write):
private _setTab(tab: string) {
  this._activeTab = tab;
  localStorage.setItem("climate-manager-tab", tab);
}
```

**Verify:** After refresh, the tab selected before refresh is still active.

**Done:** Commit includes `main.ts` change.

---

## Task 2: Period temperature in room card header

**File:** `frontend/src/components/room-card.ts`

**Current:** `_renderHeaderStatus()` shows raw `active_period` string (e.g.
"normal")

**Change:**

- Import `PERIOD_DISPLAY_NAMES` from `"../types.js"` (add to existing import)
- In `_renderHeaderStatus()`, look up display name and append temperature:

```typescript
// At top of _renderHeaderStatus():
const period = s?.active_period ?? null;
const periodLabel = period ? PERIOD_DISPLAY_NAMES[period] ?? period : "—";
const periodTempVal =
  period != null ? this.panelConfig?.period_temperatures?.[period] : undefined;
const periodDisplay =
  periodTempVal != null ? `${periodLabel} · ${periodTempVal}°C` : periodLabel;
```

Then render `${periodDisplay}` instead of `${period}`.

Note: `panelConfig` is already available on the component
(`@property() panelConfig!: ClimateConfig`).

**Verify:** Room card header clock chip shows "Normal · 20°C" style text (not
raw "normal").

**Done:** Commit includes `room-card.ts` change.
