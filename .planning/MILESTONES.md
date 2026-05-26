# Milestones

## v1.0 MVP (Shipped: 2026-05-26)

**Phases completed:** 3 phases, 14 plans  
**Timeline:** 2026-05-15 → 2026-05-26 (11 days)  
**Codebase:** ~2,000 LOC Python + ~4,100 LOC TypeScript, 168 files changed, 265 commits  
**Quick tasks shipped:** 28 post-phase improvements  
**Known deferred items at close:** 28 quick task directories missing status marker (work done, tracking artifact only)

**Key accomplishments:**

1. HACS-compatible HA custom integration — manifest, config flow, Store-backed persistence, two-call TRV control (heat mode → set_temperature; auto mode never used)
2. Full backend scheduling engine — weekday-based time programs, four period modes (frost/reduced/normal/comfort), per-room override or global inheritance, validated {mon..sun} schema
3. Person presence engine — Automatic/Present/Absent/HA modes, periodic presence schedules, room associations, occupied-window heating (presence fills gaps between Normal/Comfort periods)
4. ClimateManagerCoordinator — minute-poll control loop, concurrent asyncio.gather TRV dispatch (~10s→<1s mode-change), DST-safe wall-clock evaluation, startup push on HA restart
5. WebSocket API (8 commands) + Lit/TypeScript Lovelace panel — Global Settings (mode, temps, time program), Rooms (per-room schedule, reset-to-global), Persons (mode, room associations, presence schedule)
6. Interactive time-bar — drag-resize period boundaries with live preview, Android touch support (44px handles, touch-action, overflow:visible, e.preventDefault)

---
