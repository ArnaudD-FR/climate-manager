# Phase 15: Remove Room-Level Mode Override - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove `room_mode` entirely from every layer of the integration. Rooms have
no per-room scheduling override — they follow their zone's schedule exclusively.

**In scope:**

- `const.py`: delete `ROOM_MODE_CUSTOM`, `ROOM_MODE_GLOBAL`, `ROOM_MODE_FROST`
- `coordinator.py`: delete all `ROOM_MODE_CUSTOM` and `ROOM_MODE_FROST` branches;
  rooms always resolve via `_resolve_zone_config(area_id, config)`
- `storage.py`: compat shim strips `room_mode` and `time_program` from every
  room record on load (same lazy read-time pattern as Phase 14's `default_zone`
  shim; no write-back)
- `websocket.py`: delete `_make_ws_reset_room_to_default_zone_program` and
  its registration; ensure `set_room_config` no longer accepts `room_mode`
- `frontend/src/components/room-card.ts`: remove mode `<select>` (global /
  frost_protection / custom), inline time-bar section, `_renderRoomModeDescription()`,
  `_expanded` default tied to custom mode, and the room mode badge in the header;
  keep the active period status and zone name in the header
- `frontend/src/types.ts`: remove `room_mode` field from `RoomConfig`
- `tests/`: delete or rewrite all tests referencing `room_mode`

**Out of scope:**

- Zone-level mode changes (MODE_OFF, MODE_TIME_PROGRAM, etc.) — untouched
- Zone picker in room card — stays as-is
- Pre-heat, calendar presence, calibration — untouched
- Creating or suggesting MODE_OFF zones as frost replacements — user's responsibility

</domain>

<decisions>
## Implementation Decisions

### Storage Migration

- **D-01:** Lazy read-time compat shim in `storage.py` (same pattern as Phase 14
  `default_zone` shim). On every load, iterate `config["rooms"]` and strip
  `room_mode` and `time_program` from any room record that has them.
- **D-02:** Migration is **silent** — no log emitted for rooms that had
  `frost_protection`, `custom`, or any other `room_mode`. Applies equally to
  all modes; no special-casing. Rooms fall back to their zone on next evaluation.
- **D-03:** The shim strips `time_program` from rooms unconditionally when
  encountered (it is only meaningful alongside `room_mode: custom`). No write-back
  — old configs stay on disk until a normal `async_save()` fires.

### Coordinator

- **D-04:** Remove the `if room_mode == ROOM_MODE_FROST` and
  `if room_mode == ROOM_MODE_CUSTOM` branches from `_compute_desired_temps`
  and `_apply_presence_overrides`. The preamble comment (SCHED-05) is also
  removed. Rooms always reach `_resolve_zone_config`.
- **D-05:** Remove all other `room_config.get("room_mode")` checks (preheat
  logic at lines ~784 and ~869). The preheat path uses the zone's time_program
  exclusively.

### WebSocket API

- **D-06:** Delete `_make_ws_reset_room_to_default_zone_program` factory and
  its `websocket_api.async_register_command` call. The command
  `climate_manager/reset_room_to_default_zone_program` no longer exists.
- **D-07:** `set_room_config` schema validation: remove `room_mode` from any
  `vol.Optional` keys if present; the handler should not write `room_mode` into
  the room record.

### Frontend — Room Card

- **D-08:** Remove the mode `<select>` element (options: "Zone program",
  "Off (frost)", "Custom program") and its `@change` handler (`_onModeChange`).
- **D-09:** Remove the inline time-bar section rendered when
  `resolvedMode === "custom"` (the `${resolvedMode === "custom" ? html\`…\`}`
  block in the room config panel).
- **D-10:** Remove `_renderRoomModeDescription()` method and its call site.
- **D-11:** Remove the room mode badge from the room card header (the element
  that showed "custom" / "frost" / "Zone program" as a chip). Keep the active
  period status (e.g., "Normal") and the associated zone name — these come from
  the coordinator's `StatusPayload`, not from `room_mode`.
- **D-12:** Remove the `_expanded` default-to-true logic tied to
  `room_mode === "custom"`. Expand/collapse state defaults to collapsed (or
  whatever the prior default was for non-custom rooms).

### Frontend — Types

- **D-13:** Remove `room_mode?: "global" | "frost_protection" | "custom"` from
  the `RoomConfig` TypeScript interface in `types.ts`.

### Tests

- **D-14:** Delete tests whose sole purpose is validating `room_mode` behavior:
  `test_room_mode_custom_uses_room_time_program`,
  `test_zone_off_overrides_room_mode_custom_default_zone`,
  `test_zone_off_overrides_room_mode_custom_custom_zone`, and the
  `reset_room_to_default_zone_program` websocket tests.
- **D-15:** Any remaining tests that incidentally set `room_mode` in fixture
  data should have that key removed; tests should still pass because coordinator
  no longer reads the field.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §ARCH-02 — updated requirement definition for
  full `room_mode` removal

### Phase Dependency

- `.planning/phases/14-default-zone-consolidation/14-CONTEXT.md` — defines
  the lazy read-time compat shim pattern (D-02/D-03 from Phase 14) that this
  phase reuses for the migration shim

### Roadmap

- `.planning/ROADMAP.md` §Phase 15 — success criteria and scope boundary

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Patterns

- **Phase 14 compat shim** (`storage.py` load path): the `if "global_mode" in
  config and "default_zone" not in config` block is the exact pattern to follow
  for the room-level migration shim. Strip fields in memory; no write-back.
- **`_resolve_zone_config`** (`coordinator.py`): after removing room_mode
  branches, every room goes straight to this call — already handles Default Zone
  and custom zones uniformly.

### Touch Points

- `coordinator.py`: lines ~374–422 (`_compute_desired_temps` ROOM_MODE_FROST /
  ROOM_MODE_CUSTOM branches), lines ~517 and ~784, ~869 (preheat logic)
- `websocket.py`: lines ~550–591 (`_make_ws_reset_room_to_default_zone_program`)
  and line ~585 (`room["room_mode"] = "custom"` inside `set_room_config` flow)
- `frontend/src/components/room-card.ts`: lines ~341–353 (mode type + handler),
  ~455 (`resolvedMode`), ~646–647 (description), ~1027–1146 (mode select +
  time-bar conditional)
- `frontend/src/types.ts`: line ~59 (`room_mode?` field)
- `const.py`: lines 50–52 (three `ROOM_MODE_*` constants)

### Integration Points

- The `StatusPayload` type already carries per-room `active_period` independent
  of `room_mode` — the period status badge in the room card header reads from
  there, so it survives removal of room_mode unchanged.

</code_context>

<specifics>
## Specific Ideas

- Room card header after cleanup: active period status (e.g., "Normal — 20°C")
  and the zone name remain; the room mode badge (chip showing "custom" /
  "frost" / "Zone program") is removed. No replacement element needed.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-remove-room-custom-scheduling*
*Context gathered: 2026-06-04*
