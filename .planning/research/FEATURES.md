# Features

**Project:** Climate Manager — Home Assistant Custom Integration
**Researched:** 2026-05-15
**Confidence:** HIGH

---

## Table Stakes (must have or users leave)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Global on/off with frost protection floor | Every physical thermostat has this | Low | Safety mode, 7°C default |
| Named temperature presets with configurable defaults | Standard TRV language (eco, comfort, away) | Low | Four levels: Frost / Reduced / Normal / Comfort |
| Weekday-aware time program | Programmable thermostats have had this since the 1990s | Medium | Weekday sets + time periods mapped to named modes |
| Full 24-hour coverage with implicit midnight end | Gaps in coverage mean undefined/unsafe heating state | Low | Last period of day ends at midnight; first period of next day takes over |
| Per-room schedule or global fallback | Multi-room homes have different patterns per room | Medium | Room inherits global if no room-level program defined |
| Room → climate entity association | Nothing to control without this mapping | Low | One room → one or more HA `climate` entities |
| Correct state on HA restart (recomputed, not restored) | #1 complaint across all competing integrations | Medium | Evaluate current time slot on startup, push correct temp immediately |
| Global mode switch (Off / Time program / Time program + presence) | Users need a single master lever | Low | Three-state, persisted |
| Full UI configuration — no YAML required | HACS user expectation; YAML integrations have lower adoption | Medium | Full Lovelace panel with global settings / rooms / persons sections |

---

## Differentiators (competitive advantage)

| Feature | Value Proposition | Complexity |
|---------|-------------------|------------|
| Person presence via periodic schedule (first-class) | All competitors require external automations/blueprints for presence-linked heating | High |
| Person → room associations | Room-level presence (bedroom warms when that person is home) vs. a single global home/away flag | Medium |
| Global mode as master presence override | When "Off", presence is irrelevant; when "Time program only", presence is ignored — explicit and predictable | Low |
| Unified panel: global settings + rooms + persons in one place | Competitors have no integrated UI for schedule + presence; users stitch three separate UIs | High |
| Weekday-set grouping (not per-day) | Most schedulers force per-day or weekday/weekend binary; sets like "Mon–Thu" match how people actually live | Medium |
| Mode-named presets (not raw temperatures) | Users think "comfort", not "22°C"; named modes are more maintainable | Low |

---

## Anti-Features (deliberately NOT in v1)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Calendar-based presence (iCal, Pronote) | External HTTP dependency, auth, format parsing — disproportionate complexity | v2; periodic schedule covers regular households |
| GPS / zone-based presence | Phone app dependency, latency, false positives | v2; manual Present/Absent override covers exceptional cases |
| Specific holiday periods (date-range overrides) | Third scheduling dimension requiring priority logic on top of time programs + presence | v2; users set global mode to Off manually |
| Predictive pre-heat (start N minutes early) | Requires per-room thermal model; outside temp, insulation variables | Explicit schedule application covers the stated use case |
| Energy reporting / consumption tracking | Other integrations do this better | Use HA's built-in energy dashboard |
| Window/door open detection | Adds sensor dependency per room; Better Thermostat already does this | Users keep BT for that feature or use automations |
| Multiple simultaneous time programs per room | Conflict resolution complexity; no clear user need | One active program per room; global as fallback |
| YAML-only configuration | Reduces adoption, makes panel UX redundant | All configuration through the Lovelace panel |
| TRV brand-specific APIs | Breaks portability | Standard HA `climate` entity interface only |

---

## Critical Edge Cases

**DST (Daylight Saving Time)**
The window between 2:00–3:00 AM on DST transition days either doesn't exist (spring forward) or occurs twice (fall back). Prevention: always evaluate the active period by asking "what time is it right now?" using `dt_util.now()`. Recomputing from current time at startup eliminates DST-induced missed triggers automatically.

**Midnight crossings**
The last time period of a day has no explicit end time — it ends at midnight, at which point the next day's weekday set takes over. Without explicit day-boundary handling, periods silently stay active into the next day.

**HA restart at arbitrary time**
Competing integrations restore previous state (wrong) rather than recomputing from the current time slot. Prevention: on startup, evaluate the schedule for the current datetime and push the correct target temperature immediately.

**Conflicting weekday sets**
If the same calendar day appears in two weekday sets within one time program, the active period is ambiguous. Prevention: validate at save time that each calendar day appears in at most one weekday set. Reject invalid configs with a clear error.

**Person override vs. automatic schedule**
A person manually set to "Present" or "Absent" must fully override the periodic schedule. When set back to "Automatic", recompute immediately — don't wait for the next scheduled transition.

**All persons absent in "Time program + presence" mode**
Re-apply frost protection to all rooms not covered by a present person on any presence recalculation trigger — don't rely on the absence of a "heating on" trigger.

---

## Feature Dependencies

```
Global mode switch
  └─→ Time program evaluation
        └─→ Weekday-set + time-period data model
              └─→ Named period modes (Frost / Reduced / Normal / Comfort)
                    └─→ Default temperatures (configurable in global settings)

Per-room schedule override
  └─→ Room entity (climate entity associations)
        └─→ Falls back to global time program if no room-level program defined

Person presence (periodic schedule)
  └─→ Global mode = "Time program + presence"
        └─→ Person → room associations
              └─→ Present: room follows its time program
              └─→ Absent: room uses Frost protection

HA restart recovery
  └─→ Evaluate current datetime against active time program on startup
  └─→ Push correct temperature immediately (not after next transition)

Lovelace panel
  └─→ Global settings section (mode switch, default temperatures, global time program)
  └─→ Rooms section (per-room time program override, climate entity associations)
  └─→ Persons section (mode, room associations, periodic presence schedule)
```

---

## Open Questions

- **Presence + per-room schedule interaction:** When a person is present and their room has a time program, which temperature wins — the room's time program temperature or a hardcoded "present = Normal"? The spec implies the room's time program applies (presence just determines whether the program runs at all), but this should be validated.
- **Person "Automatic" mode with no periodic schedule configured:** Should this default to "always present" or "always absent"?
- **Multiple TRVs per room, partial unavailability:** If one TRV in a room becomes unavailable, should commands still go to the remaining TRVs? (Recommended: yes, fail-open per entity.)
- **Weekday-set editor UX:** How does the panel represent weekday set construction? No established HA pattern exists — needs custom UI design.
