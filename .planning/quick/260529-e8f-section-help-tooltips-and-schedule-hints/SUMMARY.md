---
slug: e8f
status: complete
---

Added section-label tooltips and schedule behavior hints across all three card components.

**Changes:**
- `shared-styles.ts` — new `.schedule-hint` CSS (12px secondary-text-color, 1.5 line-height)
- `zone-tab.ts` — `title` on Mode and Assigned rooms labels; `_renderScheduleHint()` below time-bar (3 variants: off / time_program / time_program_presences)
- `room-card.ts` — `title` on Mode, Schedule, Zone, Associated persons, Climate entities labels; `_renderCustomScheduleHint()` below custom time-bar (3 variants keyed to global mode)
- `person-card.ts` — `title` on Presence mode, Room associations, Presence schedule labels; static hint below presence time-bar

Commit: 2e1fb8b
