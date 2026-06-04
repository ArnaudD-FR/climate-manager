# Phase 15: Remove Room-Level Mode Override - Research

**Researched:** 2026-06-04
**Domain:** Refactor — dead code removal across Python backend, TS frontend, and tests
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Lazy read-time compat shim in `storage.py` (same pattern as Phase 14
  `default_zone` shim). On every load, iterate `config["rooms"]` and strip
  `room_mode` and `time_program` from any room record that has them.
- **D-02:** Migration is silent — no log emitted for rooms that had
  `frost_protection`, `custom`, or any other `room_mode`.
- **D-03:** The shim strips `time_program` from rooms unconditionally when
  encountered. No write-back.
- **D-04:** Remove the `if room_mode == ROOM_MODE_FROST` and
  `if room_mode == ROOM_MODE_CUSTOM` branches from `_compute_desired_temps`
  and `_apply_presence_overrides`. Rooms always reach `_resolve_zone_config`.
- **D-05:** Remove all other `room_config.get("room_mode")` checks (preheat
  logic at lines ~784 and ~869).
- **D-06:** Delete `_make_ws_reset_room_to_default_zone_program` factory and
  its `async_register_command` call.
- **D-07:** `set_room_config` schema validation: remove `room_mode` from any
  `vol.Optional` keys if present; handler must not write `room_mode` into
  the room record.
- **D-08:** Remove the mode `<select>` element and `_onRoomModeChange` handler.
- **D-09:** Remove the inline time-bar section rendered when
  `resolvedMode === "custom"`.
- **D-10:** Remove `_renderRoomModeDescription()` method and its call site.
- **D-11:** Remove the room mode badge from the room card header (chip showing
  "custom" / "frost" / "Zone program"). Keep active period status and zone name.
- **D-12:** Remove the `_expanded` default-to-true logic tied to
  `room_mode === "custom"`. Default to collapsed.
- **D-13:** Remove `room_mode?: "global" | "frost_protection" | "custom"` from
  the `RoomConfig` TypeScript interface in `types.ts`.
- **D-14:** Delete tests whose sole purpose is validating `room_mode` behavior:
  `test_room_mode_custom_uses_room_time_program`,
  `test_zone_off_overrides_room_mode_custom_default_zone`,
  `test_zone_off_overrides_room_mode_custom_custom_zone`, and the
  `reset_room_to_default_zone_program` websocket tests.
- **D-15:** Any remaining tests that incidentally set `room_mode` in fixture
  data should have that key removed; tests should still pass.

### Claude's Discretion

None — discussion stayed within phase scope.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-02 | `room_mode` removed entirely from coordinator, storage, and frontend; rooms always follow their zone's schedule; storage migration strips `room_mode` and `time_program` from all room records on load; `ROOM_MODE_*` constants and `reset_room_to_default_zone_program` WS command are deleted | All touch points identified and mapped; compat shim pattern confirmed from Phase 14 |
</phase_requirements>

## Summary

Phase 15 is a pure dead-code removal refactor across five layers: Python constants,
coordinator logic, storage migration, WebSocket API, and TypeScript frontend. No new
features are introduced; every change is a deletion or simplification. The entire
`room_mode` concept — a per-room override that let a room use a custom schedule or
lock to frost protection — is being replaced by the zone model. Rooms with a custom
schedule today simply need to be moved to a dedicated zone; the frost protection use
case is handled by a zone in MODE_OFF.

The Phase 14 lazy read-time shim pattern is the direct blueprint for the storage
migration. The shim in `storage.py:async_load` must strip `room_mode` and
`time_program` from every room record in memory on every load, without writing back.
This is strictly additive to the existing migration chain — it slots in after the
existing GAP-01 and Phase 14 shims.

The coordinator changes collapse two special-case branches (`ROOM_MODE_FROST` and
`ROOM_MODE_CUSTOM`) in `_compute_desired_temps`, one guard in
`_apply_presence_overrides`, and two preheat branch checks at lines ~784 and ~869.
After removal, every room code path flows unconditionally through
`_resolve_zone_config`. The frontend changes remove the mode select, the inline
time-bar conditional, the mode description method, and the mode badge from the card
header, leaving the period status badge and zone name badge untouched.

**Primary recommendation:** Execute in layer order — const → storage → coordinator →
websocket → frontend types → frontend component → tests. This ordering guarantees
each layer's changes are independently verifiable before the next layer is touched.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Storage migration shim | Backend (storage.py) | — | Read-time field stripping lives in the persistence layer |
| Coordinator branch removal | Backend (coordinator.py) | — | Temperature resolution logic is backend-only |
| WS command deletion | Backend (websocket.py) | Frontend (ws-client.ts) | Command must be removed on both ends |
| Frontend mode UI removal | Frontend (room-card.ts) | — | Purely presentational layer |
| Type contract cleanup | Frontend (types.ts) | — | TypeScript interface mirrors backend storage schema |
| Test cleanup | Test layer | — | Tests must reflect the new invariant: room_mode is absent |

## Standard Stack

No new external packages are introduced in this phase. All changes use the existing
project stack. [VERIFIED: codebase audit]

### Installation

None required.

## Package Legitimacy Audit

No new packages installed in this phase. Audit not applicable.

## Architecture Patterns

### Compat Shim Pattern (from Phase 14)

The Phase 14 shim in `storage.py:async_load` is the canonical reference. It runs
after the sparse deep-merge and before the function returns. The pattern:

1. Iterate the collection to migrate (`config["rooms"].values()`).
2. Pop each deprecated key unconditionally.
3. No write-back — old data stays on disk until the next normal `async_save()`.
4. Guard against key absence using `dict.pop(key, None)` rather than conditional
   checks, to handle both old and new format configs uniformly.

The Phase 14 shim guards with `if "global_mode" in stored and "default_zone" not in
stored` because the old and new formats are structurally distinct. The Phase 15 shim
needs no such guard — `room_mode` and `time_program` on a room record are always
safe to pop regardless of storage format, since they are absent in new-format rooms.

```python
# Source: storage.py Phase 14 compat shim (D-02/D-03) — lines 163–198
# Phase 15 shim inserts AFTER Phase 14 shim, BEFORE the return statement.
for room_cfg in result.get("rooms", {}).values():
    room_cfg.pop("room_mode", None)
    room_cfg.pop("time_program", None)
```

[VERIFIED: codebase audit of storage.py]

### Coordinator Simplification Pattern

After removing the two branches, `_compute_desired_temps` has a single path for
non-frost, non-off rooms: `_resolve_zone_config` → schedule evaluation → temp lookup.
The `_apply_presence_overrides` method similarly loses the early `continue` for
`ROOM_MODE_CUSTOM` rooms. The preheat method (`_async_preheat_room`) loses two
`room_cfg.get("room_mode") == ROOM_MODE_CUSTOM` branch forks.

```python
# BEFORE (coordinator.py ~374–422):
room_mode = room_config.get("room_mode", "global")
if room_mode == ROOM_MODE_FROST:
    ...  # DELETE entire block
    continue
zone_mode, zone_time_program = self._resolve_zone_config(area_id, config)
if zone_mode == MODE_OFF:
    ...  # KEEP (zone off is still valid)
    continue
if room_mode == ROOM_MODE_CUSTOM:
    ...  # DELETE entire block
    continue
# Room follows its zone schedule (this block stays, no changes)
```

[VERIFIED: codebase audit of coordinator.py lines 372–446]

### Frontend Badge Cleanup Pattern

The `render()` method in `room-card.ts` currently computes `resolvedMode`,
`badgeClass`, and `badgeText` from `this.config?.room_mode`. These three computed
values drive two distinct HTML elements: the mode badge `<span class="program-badge
${badgeClass}">` and the mode select section. Both are removed. The period badge
(`_renderPeriodBadge()`) and zone badge (`<span class="zone-badge">`) are
independent and survive — neither reads `room_mode`.

After removal, the `render()` method no longer needs `resolvedMode`, `badgeClass`,
or `badgeText`. The `resolved_mode === "frost_protection"` guard in
`_renderPeriodBadge()` (line 456) is also dead — frost rooms no longer exist — but
removing it is safe since it becomes unreachable code. The decision to remove it for
cleanliness is at the planner's discretion.

[VERIFIED: codebase audit of room-card.ts lines 1027–1183]

### Recommended Project Structure

No structural changes. All files being modified already exist.

```
custom_components/climate_manager/
├── const.py            # delete 3 ROOM_MODE_* constants (lines 50–52)
├── coordinator.py      # delete 4 room_mode branches
├── storage.py          # add Phase 15 compat shim
└── websocket.py        # delete WS factory + registration
frontend/src/
├── types.ts            # remove room_mode? field from RoomConfig
└── components/
    └── room-card.ts    # remove mode select, time-bar conditional, badge
tests/
├── test_coordinator.py # delete 5 test functions, clean 15+ incidental refs
├── test_preheat.py     # clean 1 incidental room_mode ref in fixture
├── test_storage.py     # clean 3 incidental room_mode refs in fixtures
└── test_websocket.py   # delete 2 WS tests, clean 3 incidental refs
```

### Anti-Patterns to Avoid

- **Defensive null-check after shim:** Do not add `if room_cfg.get("room_mode")`
  guards elsewhere in the coordinator after the storage shim is in place. The shim
  guarantees the field is absent; adding guards creates false safety signals.
- **Partial removal:** Do not leave `room_mode` handling in any one layer while
  removing it from others. A stale `room_mode` value in storage (un-shimmed) hitting
  coordinator code that has already removed the branch would cause silent behavior
  regression.
- **Leaving `time_program` on rooms:** The compat shim MUST also strip
  `time_program` from room records. A room with a stale `time_program` and no
  `room_mode` will have dead data in storage but will not break behavior (the
  coordinator no longer reads it). Still, stripping it keeps storage clean.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stripping stored fields on upgrade | Custom migration script | `dict.pop(key, None)` in `storage.py:async_load` | HA Store is load/save only; the existing compat shim chain handles in-memory normalization |
| Ensuring no `room_mode` in WS payloads | Schema validation | Silent drop in `set_room_config` handler (same as `preheat_enabled` GAP-01 drop at line 374) | vol schema would require `vol.Optional("room_mode")` with reject logic; silent drop is simpler and already precedented |

## Runtime State Inventory

This is a refactor/migration phase. The `room_mode` field is stored in HA's
persistent storage (`/.storage/climate_manager`).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `room_mode` and `time_program` keys in room records in `/.storage/climate_manager` | Read-time strip in `storage.py` compat shim (D-01) — no write-back required |
| Live service config | No external services reference `room_mode` | None |
| OS-registered state | None — this field is HA-internal only | None |
| Secrets/env vars | None — `room_mode` is not a secret or env var | None |
| Build artifacts | `frontend/dist/panel.js` — built artifact will be stale after TS changes | `make build && make deploy` after frontend changes |

**Critical nuance:** The storage shim strips `room_mode` from the in-memory
`runtime_config` on every load. Until the user triggers a normal `async_save()`,
the on-disk file still contains `room_mode`. This is correct and intentional per D-03
(no write-back). The coordinator never reads `room_mode` after Phase 15, so the
stale on-disk value is harmless.

## Common Pitfalls

### Pitfall 1: Wrong Shim Insertion Point

**What goes wrong:** The Phase 15 compat shim runs before the Phase 14 shim or
interleaves with the GAP-01 migration, causing the wrong in-memory state.
**Why it happens:** The shim chain in `storage.py:async_load` must run in a specific
order: GAP-01 (room preheat_enabled) → Phase 14 (global_mode → default_zone) →
Phase 15 (room_mode/time_program strip).
**How to avoid:** Insert the Phase 15 shim AFTER the Phase 14 shim block (after the
`else:` branch's day-fill pass), BEFORE the `return result` statement.
**Warning signs:** Tests that check `result["rooms"]["x"]["room_mode"]` should
confirm the key is absent after load.

### Pitfall 2: `time_program` Strip Breaks Zone Time Programs

**What goes wrong:** The shim strips `time_program` from all config dict values
found in `config["rooms"]`. If the code accidentally iterates `config` instead of
`config["rooms"]`, it would strip `time_program` from `config["default_zone"]` or
zone entries.
**Why it happens:** Typo — iterating `result.values()` instead of
`result.get("rooms", {}).values()`.
**How to avoid:** Scope the iteration explicitly to `result.get("rooms",
{}).values()`. The existing GAP-01 shim uses this exact scope.
**Warning signs:** Zone tabs render with empty schedules after Phase 15 deploys.

### Pitfall 3: Test Cleanup Misses Incidental References

**What goes wrong:** Tests pass individually but fail at collection because
`ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`, or `ROOM_MODE_CUSTOM` are still imported at
the top of `test_coordinator.py` after the functions that used them are deleted.
**Why it happens:** Python import cleanup is easy to forget when deleting functions.
**How to avoid:** After deleting test functions, remove the three `ROOM_MODE_*`
imports from `test_coordinator.py` line 39–41. Run `make test` to confirm.
**Warning signs:** `ImportError` or `F401 imported but unused` linting errors.

### Pitfall 4: `set_room_config` Still Persists `room_mode`

**What goes wrong:** A frontend caller sends `{room_mode: "global"}` in a
`set_room_config` payload; the backend handler sparse-merges it into the room record,
writing the field back despite the compat shim removing it.
**Why it happens:** The handler uses `.update(incoming_config)` which would preserve
any `room_mode` key in the payload.
**How to avoid (D-07):** Add `incoming_config.pop("room_mode", None)` in
`ws_set_room_config`, mirroring the existing `preheat_enabled` silent drop at line
374. This guards against any residual frontend call or external automation that
sends `room_mode`.
**Warning signs:** After deploying, `/.storage/climate_manager` rooms entries
re-acquire `room_mode` keys after any `set_room_config` call.

### Pitfall 5: `_renderPeriodBadge` Frost Guard Left as Dead Code

**What goes wrong:** `_renderPeriodBadge()` at line 456 checks
`if (resolvedMode === "frost_protection") return html\`\`;` where `resolvedMode`
is derived from `this.config?.room_mode`. After removing `room_mode`, `resolvedMode`
is always undefined/absent, so `this.config?.room_mode ?? "global"` always evaluates
to `"global"`. The frost guard becomes permanently dead.
**Why it happens:** Partial cleanup — the badge method is not touched when `render()`
is cleaned up.
**How to avoid:** Remove the `resolvedMode` derivation and the frost guard inside
`_renderPeriodBadge()`. The method body should start directly at the `globalMode`
check.
**Warning signs:** TypeScript strict-mode lint warning about unreachable code (if
enabled).

### Pitfall 6: `resetRoomToDefaultZoneProgram` in ws-client.ts Left Orphaned

**What goes wrong:** The method `resetRoomToDefaultZoneProgram()` in `ws-client.ts`
(line 161) is only called from `_onResetToGlobal()` in `room-card.ts`. After
removing `_onResetToGlobal()` and the Reset button from the room card, the ws-client
method becomes dead code. If not removed, TypeScript may emit a lint warning; worse,
it documents a WS command that no longer exists.
**How to avoid:** Delete `resetRoomToDefaultZoneProgram()` from `ws-client.ts`
when removing `_onResetToGlobal()` from `room-card.ts`.

## Code Examples

### Phase 15 Compat Shim (storage.py insertion point)

```python
# Source: storage.py async_load(), insert AFTER Phase 14 shim, BEFORE return result
# (after the else: day-fill block at ~lines 193–198)

# Phase 15 compat shim (D-01/D-03): strip room_mode and time_program from
# all room records on every load.  Silent — no log emitted (D-02).
# pop() is safe regardless of storage format: absent key → no-op.
for room_cfg in result.get("rooms", {}).values():
    room_cfg.pop("room_mode", None)
    room_cfg.pop("time_program", None)
```

[VERIFIED: codebase audit — follows exact GAP-01 pattern at lines 151–161]

### set_room_config Silent Drop (websocket.py)

```python
# Source: websocket.py ws_set_room_config, after the existing preheat_enabled drop
# (after line 374: incoming_config.pop("preheat_enabled", None))

# Phase 15 (D-07): room_mode is no longer a valid room key; silently drop
# it so legacy callers or residual frontend sends don't persist the field.
incoming_config.pop("room_mode", None)
```

[VERIFIED: codebase audit — mirrors GAP-01 pattern at line 374]

### Coordinator _compute_desired_temps After Removal

```python
# Source: coordinator.py _compute_desired_temps() — lines 372–446 simplified
# After removing ROOM_MODE_FROST and ROOM_MODE_CUSTOM branches:

for area_id in rooms:
    # Resolve zone config (always — room_mode no longer short-circuits)
    zone_mode, zone_time_program = self._resolve_zone_config(
        area_id, config
    )
    if zone_mode == MODE_OFF:
        # EVAL-01: zone off → frost protection for all rooms in the zone
        desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
        room_periods[area_id] = PERIOD_FROST_PROTECTION
        frost_locked_rooms.add(area_id)
        mode_off_rooms.add(area_id)
        continue
    # Room follows its zone schedule
    if zone_mode in (MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES):
        period_mode = evaluate_schedule(zone_time_program, now)
        ...
```

[VERIFIED: codebase audit of coordinator.py]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-room frost lock via `room_mode: frost_protection` | Assign room to a zone with `mode: off` | Phase 15 | User must use zone assignment instead |
| Per-room custom schedule via `room_mode: custom` + `time_program` | Assign room to a dedicated custom zone | Phase 15 | Room `time_program` field stripped from storage |

**Deprecated/outdated after Phase 15:**
- `ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`, `ROOM_MODE_CUSTOM` in `const.py`
- `reset_room_to_default_zone_program` WS command
- `room_mode` field in RoomConfig TypeScript interface
- `_renderRoomModeDescription()` method
- `_onRoomModeChange()` handler
- `_onResetToGlobal()` handler
- `resetRoomToDefaultZoneProgram()` in ws-client.ts

## Assumptions Log

All claims in this research were verified or cited — no user confirmation needed.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **`_renderPeriodBadge()` frost guard cleanup scope**
   - What we know: The `resolvedMode === "frost_protection"` guard at line 456
     becomes unreachable after removing `room_mode`. The method still functions
     correctly (the guard just never fires).
   - What's unclear: Whether the planner should include removal of this dead code
     as an explicit task or treat it as optional cleanup.
   - Recommendation: Include it as part of the room-card cleanup task to keep the
     method free of dead references.

2. **`test_room_mode_frost_protection_pushes_frost_temp` — delete or rewrite?**
   - What we know: This test verifies that `room_mode: frost_protection` produces
     frost temp. After Phase 15, the behavior it tests no longer exists.
   - What's unclear: Whether a replacement test for zone-MODE_OFF frost behavior
     is warranted (that behavior is already covered by
     `test_zone_mode_off_pushes_frost_temp` at line 1405).
   - Recommendation: Delete this test; the zone-level frost test covers the
     surviving path. No replacement needed.

3. **`test_room_mode_absent_key_uses_global_program` — delete or rewrite?**
   - What we know: Tests that a room with no `room_mode` follows the zone program —
     which is now the only behavior. The invariant is vacuously always true.
   - Recommendation: Delete (no longer a meaningful test case). The surviving
     `test_room_mode_global_explicit_key_uses_global_program` also falls in this
     category and should be deleted too — the "explicit global key" case no longer
     exists either.

## Environment Availability

Step 2.6: SKIPPED — Phase 15 is a code/storage-layer removal with no new external
dependencies. The existing build toolchain (`make build`, `make test`) is sufficient.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-homeassistant-custom-component |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `make test` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-02 | `room_mode` absent from all room records after load | unit | `make test` (test_storage.py — new shim test) | Wave 0 gap |
| ARCH-02 | `time_program` absent from room records after load | unit | `make test` (test_storage.py — new shim test) | Wave 0 gap |
| ARCH-02 | `ROOM_MODE_*` constants deleted from const.py | static | `make lint` + import verification | n/a (deletion) |
| ARCH-02 | `reset_room_to_default_zone_program` WS command absent | unit | `make test` (existing `test_ws_reset_room_to_global_program_is_removed` pattern) | Wave 0 gap (new assertion) |
| ARCH-02 | All existing tests pass with no `room_mode` fixture data | integration | `make test` | existing |

### Sampling Rate

- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_storage.py` — Phase 15 compat shim test: verify `room_mode` and
  `time_program` are absent from room records after `async_load()` when stored data
  contains them (mirrors `test_load_legacy_flat_keys_builds_default_zone` pattern)
- [ ] `tests/test_websocket.py` — verify `reset_room_to_default_zone_program`
  command no longer exists (send it, expect `success: False` — mirrors existing
  `test_ws_reset_room_to_global_program_is_removed` pattern)

## Security Domain

This phase performs no authentication, authorization, or data-input handling changes.
All removed WebSocket commands were write commands, but their removal reduces attack
surface rather than expanding it. No ASVS categories are newly triggered.

| ASVS Category | Applies | Note |
|---------------|---------|------|
| V5 Input Validation | yes (existing) | `set_room_config` gains a `room_mode` silent-drop guard (D-07) — reduces accepted input surface |
| All others | unchanged | No new auth, session, crypto, or access control paths |

## Detailed Touch Point Map

This table is the single authoritative source for the planner on where to make
changes. All line numbers are approximate — verify before editing.

### Backend

| File | Location | Change |
|------|----------|--------|
| `const.py` | Lines 50–52 | Delete `ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`, `ROOM_MODE_CUSTOM` constants |
| `coordinator.py` | Lines ~374–384 | Delete `if room_mode == ROOM_MODE_FROST` block and `room_mode = room_config.get(...)` preamble |
| `coordinator.py` | Lines ~404–422 | Delete `if room_mode == ROOM_MODE_CUSTOM` block |
| `coordinator.py` | Lines ~516–519 | Delete `if room_config.get("room_mode", "global") == ROOM_MODE_CUSTOM: continue` guard in `_apply_presence_overrides` |
| `coordinator.py` | Lines ~784–789 | Delete `if room_cfg_step2.get("room_mode") == ROOM_MODE_CUSTOM` branch in preheat step 2 |
| `coordinator.py` | Lines ~869–874 | Delete `if room_cfg.get("room_mode") == ROOM_MODE_CUSTOM` branch in preheat trigger |
| `coordinator.py` | Lines ~360–366 | Delete docstring bullet points referencing `room_mode` priorities (EVAL-05, SCHED-05) |
| `storage.py` | After line ~198 (else block) | Add Phase 15 compat shim — strip `room_mode` + `time_program` from room records |
| `websocket.py` | Lines 1–60 (docstring) | Update module docstring: remove `reset_room_to_default_zone_program` from command list; add "Removed in Phase 15" note |
| `websocket.py` | ~Line 110 | Delete `websocket_api.async_register_command(hass, _make_ws_reset_room_to_default_zone_program(entry))` |
| `websocket.py` | Lines 550–591 | Delete `_make_ws_reset_room_to_default_zone_program` factory function |
| `websocket.py` | Lines ~374 | Add `incoming_config.pop("room_mode", None)` in `ws_set_room_config` (D-07) |

### Frontend

| File | Location | Change |
|------|----------|--------|
| `types.ts` | Line ~59 | Delete `room_mode?: "global" \| "frost_protection" \| "custom"` from `RoomConfig` |
| `types.ts` | Line ~60 | Delete `time_program?: DailyProgram \| null` from `RoomConfig` (only meaningful alongside `room_mode`) |
| `room-card.ts` | Line ~60 | Update JSDoc comment on `_expanded` (remove reference to `room_mode: custom`) |
| `room-card.ts` | Lines ~337–363 | Delete `_onRoomModeChange()` method |
| `room-card.ts` | Lines ~399–407 | Delete `_onResetToGlobal()` method |
| `room-card.ts` | Lines ~454–456 | Remove `resolvedMode` derivation from `_renderPeriodBadge()` and frost guard |
| `room-card.ts` | Lines ~642–652 | Delete `_renderRoomModeDescription()` method |
| `room-card.ts` | Lines ~1027–1041 | Delete `resolvedMode`, `badgeClass`, `badgeText` computed values in `render()` |
| `room-card.ts` | Lines ~1054–1059 | Delete mode badge `<span class="program-badge ${badgeClass}">` element |
| `room-card.ts` | Lines ~1085–1118 | Delete Mode section: section-label + select-wrapper + `_renderRoomModeDescription()` call |
| `room-card.ts` | Lines ~1145–1168 | Delete inline time-bar conditional block (`resolvedMode === "custom"` section) |
| `room-card.ts` | Lines ~1163–1166 | Delete Reset button (`_onResetToGlobal` call site) |
| `ws-client.ts` | Lines ~158–166 | Delete `resetRoomToDefaultZoneProgram()` method |

### Tests

| File | Function(s) | Change |
|------|-------------|--------|
| `test_coordinator.py` | `test_room_mode_frost_protection_pushes_frost_temp` | Delete |
| `test_coordinator.py` | `test_room_mode_custom_uses_room_time_program` | Delete |
| `test_coordinator.py` | `test_room_mode_global_explicit_key_uses_global_program` | Delete |
| `test_coordinator.py` | `test_room_mode_absent_key_uses_global_program` | Delete |
| `test_coordinator.py` | `test_room_mode_frost_wins_over_stale_time_program` | Delete |
| `test_coordinator.py` | `test_room_mode_frost_wins_over_presence` | Delete |
| `test_coordinator.py` | `test_zone_off_overrides_room_mode_custom_default_zone` | Delete |
| `test_coordinator.py` | `test_zone_off_overrides_room_mode_custom_custom_zone` | Delete |
| `test_coordinator.py` | `test_room_mode_custom_wins_over_active_zone_schedule` | Delete |
| `test_coordinator.py` | lines 39–41 imports | Delete `ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`, `ROOM_MODE_CUSTOM` imports |
| `test_coordinator.py` | line 45 comment + `ALL_DAYS_COMFORT_PROGRAM` | Keep `ALL_DAYS_COMFORT_PROGRAM` if used by any surviving test; remove comment referencing `room_mode` |
| `test_preheat.py` | line 34 import, line 531 fixture | Remove `ROOM_MODE_FROST` import; replace `"room_mode": ROOM_MODE_FROST` with empty room config (frost-locked rooms in preheat are gated by `self._frost_locked_rooms`, not `room_mode`) |
| `test_storage.py` | lines 214, 233, 270 | Remove `room_mode` keys from fixture dicts; tests should still pass |
| `test_websocket.py` | `test_ws_reset_room_to_default_zone_program_copies_into_room` | Delete |
| `test_websocket.py` | `test_ws_reset_room_to_global_program_is_removed` | Rewrite as Phase 15 equivalent: verify `reset_room_to_default_zone_program` also returns error |
| `test_websocket.py` | lines 560, 564, 584 (`reset_room_to_default_zone_program` test) | Covered by deletion above |
| `test_websocket.py` | lines 1147, 1164 | Remove `room_mode: global` from fixture dicts; update assertion on line 1164 |
| `test_websocket.py` | lines 1186, 1197 | Remove `room_mode: custom` from test payload and remove `room_mode` assertion |

## Sources

### Primary (HIGH confidence)

- Codebase audit — `coordinator.py`, `storage.py`, `websocket.py`, `const.py`,
  `frontend/src/types.ts`, `frontend/src/components/room-card.ts`,
  `frontend/src/ws-client.ts`, `tests/test_coordinator.py`,
  `tests/test_storage.py`, `tests/test_websocket.py`, `tests/test_preheat.py`
- Phase 14 CONTEXT.md — compat shim pattern (D-02/D-03) and touch points
- Phase 15 CONTEXT.md — all implementation decisions (D-01 through D-15)

### Secondary (MEDIUM confidence)

- REQUIREMENTS.md §ARCH-02 — acceptance criteria
- STATE.md — project position and history

## Metadata

**Confidence breakdown:**
- Touch point map: HIGH — verified line-by-line against live source
- Compat shim pattern: HIGH — direct copy of Phase 14 pattern from live code
- Test cleanup map: HIGH — all test functions enumerated from grep output
- Frontend removal scope: HIGH — all elements traced to their render call sites

**Research date:** 2026-06-04
**Valid until:** This research is tied to the current codebase commit state. Any
commit that touches the listed files before Phase 15 execution may shift line
numbers. Re-read the listed files if more than one working session elapses before
planning begins.
