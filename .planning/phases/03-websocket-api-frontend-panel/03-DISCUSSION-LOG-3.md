# Phase 3: WebSocket API & Frontend Panel - Discussion Log (Session 3)

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in CONTEXT.md — this log preserves the
> alternatives considered.

**Date:** 2026-05-26 **Phase:** 03-websocket-api-frontend-panel **Areas
discussed:** Room card period badge — layout, style, and placement

---

## Room Card Period Badge

### Status line placement

| Option            | Description                                                                        | Selected |
| ----------------- | ---------------------------------------------------------------------------------- | -------- |
| Remove from row 2 | Period lives only in row 1. Status line becomes 3 items: temp + humidity + persons | ✓        |
| Keep in both      | Period appears in row 1 as colored badge AND in the status line clock item         |          |

**User's choice:** Remove from row 2 — avoids duplication.

---

### Visual style

| Option                         | Description                                      | Selected |
| ------------------------------ | ------------------------------------------------ | -------- |
| Same badge style as mode badge | Pill badge with period's color as background     | ✓        |
| Colored dot + text             | Small colored circle followed by period name     |          |
| Colored text only              | Period name in the period's color, no background |          |

**User's choice:** Same badge style as mode badge — consistent with existing
mode badge pattern.

---

### Badge content

| Option                    | Description           | Selected |
| ------------------------- | --------------------- | -------- |
| Period name only          | e.g., "Normal"        |          |
| Period name + temperature | e.g., "Normal · 19°C" | ✓        |

**User's choice:** Period name + temperature — more informative.

---

### Row 1 layout (badge ordering)

User raised: when global mode is off, room configuration is not applicable —
should the period/off indicator come before the room mode badge?

| Option                   | Description                                                       | Selected |
| ------------------------ | ----------------------------------------------------------------- | -------- |
| Period after mode badge  | [room name] [Global program] [Normal · 19°C]                      |          |
| Period before mode badge | [room name] [Normal · 19°C] [Global program] — global state leads | ✓        |
| Off replaces mode badge  | When global mode is off, room mode badge hidden                   |          |

**User's choice:** Period before mode badge — global state shown first, room
config follows.

**Notes:** User requested ASCII previews of all states before deciding. Previews
shown for: active time_program, custom room override, frost protection room
mode, and global mode off.

---

### Frost protection room mode

| Option                      | Description                                      | Selected |
| --------------------------- | ------------------------------------------------ | -------- |
| No period badge             | Mode badge "Frost protection" already conveys it | ✓        |
| Show temperature badge only | Show just "12°C" without period name             |          |
| Show full badge anyway      | Always show period badge regardless of room mode |          |

**User's choice:** No period badge — mode badge already conveys the state.

---

### Global mode off badge

| Option            | Description                             | Selected |
| ----------------- | --------------------------------------- | -------- |
| Gray badge        | Show "Off" in a gray/neutral badge      | ✓        |
| Hide period label | No period badge when global mode is off |          |

**User's choice:** Gray badge showing "Off" — room mode badge still visible
after it.

---

## Claude's Discretion

- Gray color for "Off" badge: use `--secondary-background-color` /
  `--secondary-text-color` (HA CSS variables per D-27).

## Deferred Ideas

None.
