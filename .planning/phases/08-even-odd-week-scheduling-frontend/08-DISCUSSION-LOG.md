# Phase 8: Even/Odd Week Scheduling — Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 8-even-odd-week-scheduling-frontend
**Areas discussed:** Schedule-type control, Week-switcher appearance,
Default active week, Reset button behavior

---

## Schedule-Type Control

### Q1: Where should the schedule-type control live?

| Option | Description | Selected |
|--------|-------------|----------|
| After the mode selector | Below presence mode select, co-located with scheduling | |
| Before the time-bar | Inside the schedule section, above the Even/Odd toggle | ✓ |
| You decide | Claude picks position | |

**User's choice:** Before the time-bar (inside the schedule section)
**Notes:** Keeps the schedule section self-contained — the type selector and
the week switcher are co-located with the time-bar they control.

### Q2: What control type for schedule-type toggle?

| Option | Description | Selected |
|--------|-------------|----------|
| Native `<select>` dropdown | Options: Single week / Even/Odd weeks | ✓ |
| Two inline buttons | CSS button tabs style | |
| Checkbox / toggle | 'Alternating weeks' checkbox | |

**User's choice:** Native `<select>` — consistent with presence mode and zone
picker throughout the card.

### Q3: Section label above the schedule-type select?

| Option | Description | Selected |
|--------|-------------|----------|
| Schedule type | Matches 'Presence mode' label style | ✓ |
| Alternating weeks | Descriptive of use case | |
| You decide | Claude picks | |

**User's choice:** "Schedule type"

---

## Week-Switcher Appearance

### Q1: How should the Even/Odd week switcher look?

| Option | Description | Selected |
|--------|-------------|----------|
| CSS button tabs | `[Even] [Odd]` using `.tab-btn`/`.tab-btn.active` | ✓ |
| Native `<select>` | Small select with Even week / Odd week | |
| You decide | Claude picks | |

**User's choice:** CSS button tabs — established HA 2026.x pattern from main.ts.
Preview confirmed: `[ Even ] [ Odd ]` above the time-bar.

### Q2: Position relative to section label and time-bar?

| Option | Description | Selected |
|--------|-------------|----------|
| Below section label, above time-bar | 'Presence schedule' → tabs → time-bar | ✓ |
| Above section label | Switcher first, then label | |
| You decide | Claude picks | |

**User's choice:** Below section label, above time-bar.

---

## Default Active Week

### Q1: Which week shows first when card opens for an even/odd person?

| Option | Description | Selected |
|--------|-------------|----------|
| Current ISO week parity | Today's week number determines Even/Odd tab | ✓ |
| Always Even | Simpler, no date logic needed | |
| You decide | Claude picks | |

**User's choice:** Current ISO week parity — user sees the schedule the
backend is currently evaluating.

---

## Reset Button Behavior

### Q1: What should 'Reset to default' do in even/odd mode?

| Option | Description | Selected |
|--------|-------------|----------|
| Reset only the active week | Saves DEFAULT_SCHEDULE to active week's field | ✓ |
| Reset both weeks at once | One click resets schedule_even and schedule_odd | |

**User's choice:** Reset only the active week — the other week's schedule is
untouched.

### Q2: Should the button label update to reflect the active week?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — dynamic label | 'Reset Even week to default' / 'Reset Odd week to default' | ✓ |
| No — keep 'Reset to default' | Same label in all modes | |
| You decide | Claude picks | |

**User's choice:** Yes, dynamic label — makes the scope immediately clear.

---

## Claude's Discretion

- `getWeekParity()` helper implementation — ISO week formula approach in JS
- Whether to show a `.schedule-hint` near the Even/Odd switcher
- Whether `.tab-btn` styles are re-declared locally or extracted to shared styles
- Module location for `getWeekParity()` helper

## Deferred Ideas

None — discussion stayed within phase scope.
