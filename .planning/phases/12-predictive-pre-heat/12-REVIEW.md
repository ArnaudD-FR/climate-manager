---
phase: 12-predictive-pre-heat
reviewed: 2026-06-03T08:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/websocket.py
  - custom_components/climate_manager/storage.py
  - custom_components/climate_manager/const.py
  - tests/test_preheat.py
  - frontend/src/types.ts
  - frontend/src/ws-client.ts
  - frontend/src/components/zone-tab.ts
  - frontend/src/components/room-card.ts
findings:
  blocker: 1
  warning: 3
  info: 1
  total: 5
status: issues
scope: gap-closure plans 12-06 (zone-scoped preheat backend) and 12-07 (zone-scoped preheat frontend)
---

# Code Review — Phase 12 Gap Closure (12-06 / 12-07)

Reviewed the 9 changed files for the refactor moving `preheat_enabled` from
per-room to per-zone scope.

---

## Blockers

### CR-01: Default Zone pre-heat checkbox always shows unchecked

**File:** `frontend/src/main.ts` (synthesized zoneConfig for Default Zone)

The synthesized `zoneConfig` object passed to `<climate-manager-zone-tab>` for
the Default Zone is built from `{ name, mode, time_program }` only.
`preheat_enabled` is never included. `zone-tab.ts` binds
`.checked=${this.zoneConfig?.preheat_enabled ?? false}` — which always resolves
to `false` regardless of what is saved in storage.

**Effect:** The toggle visually resets to unchecked after every `reloadConfig()`
call, making it appear saves fail. The write path (`setZonePreheat("default",
enabled)`) is correct; only the read/display is broken.

**Fix:** Add `preheat_enabled: this._config!.default_zone_preheat_enabled ?? false`
to the synthesized Default Zone zoneConfig object in `main.ts`.

`room-card.ts` is NOT affected — it reads `panelConfig.default_zone_preheat_enabled`
directly and correctly.

---

## Warnings

### WR-01: Rollback stores `null` instead of popping absent key

**File:** `custom_components/climate_manager/websocket.py` (ws_set_zone_preheat)

When `default_zone_preheat_enabled` was never set and `async_save` fails, the
rollback path does `runtime_config["default_zone_preheat_enabled"] = None`
(old_val was None from `.get()`). This persists `null` to storage on the next
save, violating the sparse model. Currently correct by accident (coordinator
uses truthiness), but fragile.

**Fix:** Use `pop` when restoring to absent:
```python
if old_val is None:
    runtime_config.pop("default_zone_preheat_enabled", None)
else:
    runtime_config["default_zone_preheat_enabled"] = old_val
```

### WR-02: `_preheat_target` not cleared on disable early-return

**File:** `custom_components/climate_manager/coordinator.py` (_async_preheat_room)

Disable early-return path clears `_preheat_active`, `_preheat_suppressed`, and
`_preheat_in_progress` but not `_preheat_target`. Stale target propagates in
status push payloads (`preheat_active=False, preheat_target=<old float>`). No
current UI regression (room-card guards on `preheatActive`), but semantically
incoherent for future consumers.

**Fix:** Add `room_state["_preheat_target"] = None` in the early-return block.

### WR-03: Schema doc still names deprecated key `preheat_lead_minutes`

**File:** `custom_components/climate_manager/const.py`

Persons sub-schema comment documents `"preheat_lead_minutes"` — renamed to
`wakeup_advance_minutes` in Phase 12. Misleads future developers.

**Fix:** Update the comment to `wakeup_advance_minutes`.

---

## Info

### IN-01: `next_occupied_at` called twice per person in suppression check

**File:** `custom_components/climate_manager/coordinator.py`

Results from the step-2 `next_occupied_at` calls could be reused in the
suppression check (lines 700-706) instead of calling again. No performance
impact (pure Python, no I/O), but unnecessary duplication.

---

## Summary

| Severity | Count |
|----------|-------|
| Blocker  | 1     |
| Warning  | 3     |
| Info     | 1     |
| **Total**| **5** |

**CR-01 has user-visible impact** — Default Zone pre-heat toggle always renders
unchecked after config reload. One-line fix in `frontend/src/main.ts`.
