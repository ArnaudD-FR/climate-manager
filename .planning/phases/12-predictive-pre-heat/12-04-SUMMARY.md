---
phase: 12-predictive-pre-heat
plan: "04"
subsystem: frontend
tags: [typescript, lit, frontend, preheat, room-card, types]

requires:
  - phase: 12-predictive-pre-heat
    plan: "02"
    provides: preheat_active/preheat_target/preheat_suppressed on status
      payload + coordinator engine
    this-uses: preheat_active, preheat_target, preheat_suppressed (consumed
      in _renderPreheatSection via roomStatus)
  - phase: 12-predictive-pre-heat
    plan: "03"
    provides: ws_get_status preheat parity + ws_set_room_config validation
    this-uses: setRoomConfig({ preheat_enabled, preheat_max_lead_minutes })
      accepted and validated on backend

provides:
  - preheat_enabled and preheat_max_lead_minutes on RoomConfig (D-01)
  - preheat_active, preheat_target, preheat_suppressed on RoomStatus (D-10)
  - wakeup_advance_minutes on PersonConfig replacing preheat_lead_minutes (D-02)
  - _renderPreheatSection() in room-card.ts with auto-save toggle + number
    input + status lines (D-11)

affects:
  - All consumers of RoomConfig, RoomStatus, PersonConfig types

tech-stack:
  added: []
  patterns:
    - _onPreheatToggle / _onPreheatMaxLeadChange mirror _onZoneChange
      try/catch + reloadConfig + showToast pattern
    - _renderPreheatSection uses native <input type="checkbox"> and
      <input type="number"> (HA 2026.x native control requirement)
    - Max lead guard: NaN or outside [0,480] returns early before WS send
      (T-12-08 defense in depth)

key-files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/components/room-card.ts
    - frontend/src/components/person-card.ts

key-decisions:
  - "D-01: preheat_enabled and preheat_max_lead_minutes added as sparse
    optional fields on RoomConfig — absent = default (false / 120 min)"
  - "D-02: PersonConfig.preheat_lead_minutes renamed to
    wakeup_advance_minutes; person-card.ts updated at both read and write
    sites"
  - "D-10: RoomStatus carries preheat_active, preheat_target, preheat_suppressed
    as optional fields matching the backend status payload"
  - "D-11: _renderPreheatSection inserted after _renderTrvSection; max-lead
    input only rendered when preheat_enabled is true; suppression warning
    only shown when both enabled and suppressed are true"
  - "T-12-08: client-side [0,480] int guard in _onPreheatMaxLeadChange
    drops invalid input before WS send (backend clamp in 12-03 is
    authoritative)"

requirements-completed: [PREHEAT-01, PREHEAT-04]

duration: ~3min
completed: 2026-06-02
---

# Phase 12 Plan 04: Frontend Pre-Heat UI Summary

**Pre-heat toggle + max lead time input with auto-save, active/suppressed
status lines in room card using native HTML controls (D-11, PREHEAT-01,
PREHEAT-04)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-02T18:53:32Z
- **Completed:** 2026-06-02T18:56:38Z
- **Tasks:** 2 (Task 1: types.ts; Task 2: room-card.ts)
- **Files modified:** 3

## Accomplishments

- Extended `RoomConfig` with `preheat_enabled?: boolean` and
  `preheat_max_lead_minutes?: number` (sparse, absent = default)
- Extended `RoomStatus` with `preheat_active?: boolean`,
  `preheat_target?: number | null`, `preheat_suppressed?: boolean`
- Renamed `PersonConfig.preheat_lead_minutes` to `wakeup_advance_minutes`
  (D-02); updated both read and write sites in `person-card.ts`
- Added `_onPreheatToggle` and `_onPreheatMaxLeadChange` handlers to
  `room-card.ts` mirroring the `_onZoneChange` try/catch + showToast pattern
- Added `_renderPreheatSection()` rendering:
  - Section label "Pre-heat"
  - Native `<input type="checkbox">` bound to `preheat_enabled` with auto-save
  - Conditional native `<input type="number">` (min=0 max=480 step=5) for
    `preheat_max_lead_minutes`, shown only when enabled
  - "Pre-heating (→ XX.X°C)" status line gated on `preheat_active &&
    preheat_target != null`
  - Suppression warning gated on `preheat_enabled && preheat_suppressed`
- Inserted `${this._renderPreheatSection()}` after `${this._renderTrvSection()}`
- `make build` and `make lint` both exit 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend types.ts** - `632ea59` (feat)
2. **Task 2: Add pre-heat section to room card** - `c65bfb7` (feat)

## Files Created/Modified

- `frontend/src/types.ts` — Added preheat fields to RoomConfig (D-01),
  RoomStatus (D-10); renamed PersonConfig field to wakeup_advance_minutes
  (D-02)
- `frontend/src/components/room-card.ts` — Added _onPreheatToggle,
  _onPreheatMaxLeadChange, _renderPreheatSection; inserted section call
  after _renderTrvSection in render()
- `frontend/src/components/person-card.ts` — Updated two sites from
  preheat_lead_minutes to wakeup_advance_minutes (read at line 938,
  write at line 628)

## Decisions Made

- Native HTML controls only: `<input type="checkbox">` and
  `<input type="number">` — ha-textfield and ha-select are broken in
  HA 2026.x (project memory constraint)
- Suppression warning is NOT shown when pre-heat is disabled — only when
  `preheat_enabled && preheat_suppressed` are both true (per D-11 context
  spec)
- Client-side guard in `_onPreheatMaxLeadChange` drops NaN and out-of-range
  values without calling setRoomConfig (T-12-08 defense in depth; backend
  12-03 clamp is authoritative)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Prettier reformatted room-card.ts on pre-commit**

- **Found during:** Task 2 commit
- **Issue:** Prettier reformatted the file, failing the pre-commit hook.
  The commit was rejected with "files were modified by this hook".
- **Fix:** Re-staged the prettier-formatted file and committed again.
- **Files modified:** frontend/src/components/room-card.ts
- **Impact:** None — formatting is compliant; no logic changed.

## Known Stubs

None. All pre-heat fields are wired to the live status payload and
ws.setRoomConfig; no placeholder values flow to the UI.

## Threat Flags

None — T-12-08 (client-side [0,480] guard) implemented as planned.
No new trust-boundary surface beyond what the plan's threat model covers.

## Self-Check

Files exist:

- frontend/src/types.ts: FOUND
- frontend/src/components/room-card.ts: FOUND
- frontend/src/components/person-card.ts: FOUND

Commits exist:

- 632ea59 (Task 1): FOUND
- c65bfb7 (Task 2): FOUND

Build: make build exits 0
Lint: make lint exits 0

## Self-Check: PASSED

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-02*
