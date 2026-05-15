# Pitfalls

**Project:** Climate Manager — Home Assistant Custom Integration
**Researched:** 2026-05-15
**Confidence:** HIGH for HA structural pitfalls; MEDIUM for scheduling edge cases; HIGH for TRV-specific issues

---

## Critical Pitfalls (rewrites or silent failures if missed)

### C1 — No catch-up logic on HA restart
**What goes wrong:** HA time triggers never fire retroactively. If the integration relies solely on scheduled events, any restart leaves TRVs at the wrong temperature until the next period boundary. This is the #1 real-world failure across all competing heating integrations.
**Warning signs:** Works fine in development; breaks in production after first HA update or reboot.
**Prevention:** On `async_added_to_hass`, evaluate the schedule for `dt_util.now()` and push the correct target temperature to all TRVs immediately — before waiting for any scheduled trigger.
**Phase:** Foundation / Coordinator (Phase 1 + 3)

---

### C2 — DST transition breaks the scheduler
**What goes wrong:** Two distinct failure modes:
- Spring forward: the 2:00–3:00 AM window doesn't exist — a period starting in that window is never triggered
- Fall back: that window occurs twice — a period can double-trigger or crash if the scheduler doesn't de-duplicate

**Warning signs:** Reports of "heating didn't come on" or duplicate service call errors on DST change nights.
**Prevention:** Always use `dt_util.now()` (HA-aware, timezone-correct) — never `datetime.now()`. Evaluate the active period from current wall time rather than tracking transitions; restart catch-up logic (C1) also handles the DST recovery automatically.
**Phase:** Scheduling Engine (Phase 2)

---

### C3 — TRV unavailability causes silent schedule failure
**What goes wrong:** `climate.set_temperature` called on an unavailable entity silently no-ops. Tado X via Matter goes unavailable intermittently during Thread network instability. The room stays at the wrong temperature indefinitely until the next scheduled transition.
**Warning signs:** Room temperature not following schedule after any network or TRV pairing event.
**Prevention:** Subscribe to `state_changed` events on all managed climate entity IDs. When a TRV transitions from `unavailable` → any other state, re-apply the current active setpoint immediately.
**Phase:** TRV Control Layer (Phase 3)

---

### C4 — Manual TRV adjustment conflict
**What goes wrong:** User manually adjusts a TRV via the Tado app or HA frontend. The next schedule transition overwrites it silently — or worse, the integration detects the state change and immediately fights back, causing a write-storm.
**Warning signs:** TRV "bouncing" between temperatures, or user frustration that manual adjustments don't stick.
**Prevention:** Define a clear contract: the integration owns TRV temperature entirely when active. Document this explicitly. Do not subscribe to TRV `state_changed` as a trigger for re-applying setpoints — only apply on schedule transitions and startup. TRV state changes from manual adjustments are read-only for the integration.
**Phase:** TRV Control Layer (Phase 3)

---

### C5 — Blocking I/O in async context
**What goes wrong:** Any `open()`, `json.load()`, or synchronous file read in an `async def` function blocks the HA event loop. In HA 2025+, this is detected and causes integration crashes or logged errors.
**Warning signs:** `RuntimeWarning: coroutine was never awaited`, event loop blocking warnings in HA logs.
**Prevention:** Use only `homeassistant.helpers.storage.Store` for all persistence. Never use direct file I/O in async functions. Set `serialize_in_event_loop=False` on the Store for large nested objects.
**Phase:** Foundation (Phase 1) — get this right from the start

---

## Moderate Pitfalls (quality gate or logic bugs)

### M1 — HACS / HA quality-scale rejection for missing structure
**What goes wrong:** HACS and the HA quality checker require specific files and fields. Missing any of the following is sufficient for rejection: `async_unload_entry` in `__init__.py`, `unique_id` on all entities, translation strings in `strings.json`, `version` field in `manifest.json`, brand assets (`brands` repo), `config_flow: true` in manifest.
**Prevention:** Start from `ludeeus/integration_blueprint`. It includes the correct structure, GitHub Actions CI with `hassfest` and HACS action, and pytest scaffold. Add `unique_id` to every entity from the first commit.
**Phase:** Foundation (Phase 1)

---

### M2 — Frontend panel JS not served correctly
**What goes wrong:** HA does not auto-serve files in `custom_components/`. The static path must be explicitly registered. Additionally, `hass.http.register_static_path()` must be called *before* `frontend.async_register_panel()` — reversing the order causes the panel to load but its JS 404s.
**Warning signs:** Panel shows blank page; browser console shows 404 for the JS module URL.
**Prevention:** Register static path first in `async_setup` (not `async_setup_entry`). Serve from `custom_components/climate_manager/www/` at `/local/climate_manager/`. Verify against current HA core source at build time.
**Phase:** Frontend Panel (Phase 5)

---

### M3 — Midnight crossing and back-to-back period boundary races
**What goes wrong:** Two related bugs:
1. Last period of the day has no explicit end — without day-boundary logic it stays active into the next day
2. Two period boundaries scheduled very close together (e.g., 08:00 and 08:01) can race if the HA event loop is busy

**Prevention:** When evaluating the active period, explicitly handle the midnight boundary: after exhausting all periods for the current day, advance to the next calendar day. For near-simultaneous boundaries, the coordinator's single-threaded refresh function ensures only one evaluation runs at a time.
**Phase:** Scheduling Engine (Phase 2)

---

### M4 — Presence schedule and period boundary ordering ambiguity
**What goes wrong:** A person transitions from absent → present at exactly the same second as a scheduled period boundary. Two events fire simultaneously. The result depends on event loop ordering — wrong temperature can be applied.
**Prevention:** Use a single `evaluate_all_rooms()` function that computes both schedule and presence state together for a given datetime. Never update temperature from two separate code paths that can interleave. Coordinator calls this function as a single atomic operation.
**Phase:** Coordinator (Phase 3)

---

### M5 — `async_unload_entry` not cancelling scheduled callbacks
**What goes wrong:** If `async_unload_entry` doesn't cancel the `async_track_point_in_time` callback and the state change listener, the integration leaves ghost listeners in the HA event loop. These fire after unload, accessing a torn-down coordinator — causing errors or phantom TRV changes.
**Prevention:** Store all cancel callbacks returned by `async_track_*` in the coordinator. Call all of them in `async_unload_entry` before returning.
**Phase:** Coordinator (Phase 3)

---

## Minor Pitfalls (correctness / maintainability)

### m1 — `git+https` in `manifest.json` requirements breaks HACS install
HACS does not support git URL requirements. All Python dependencies must be PyPI packages. This integration has no external Python deps (all HA built-ins), so this is not a risk — but do not add any git-URL deps later.

### m2 — Entity naming violates `has-entity-name` convention
HA 2023+ enforces that entities set `_attr_has_entity_name = True` and provide a `_attr_name` that is the entity's role within its device, not a globally unique name. Violations are flagged by `hassfest`. Build with this from the start.

### m3 — Frontend panel breaks on HA minor version updates
HA exposes internal `<ha-*>` web components to custom panels. These components can change between minor versions. Prevention: pin to documented component APIs where they exist; avoid relying on undocumented internal component behavior. Test against HA updates in CI with `pytest-homeassistant-custom-component`.

### m4 — Schedule config stored in `config_entry.data` instead of `Store`
`config_entry.data` is designed for immutable setup data (e.g., a hub IP address). Storing large mutable schedule structures there bypasses the `Store`'s serialization safety and can cause config corruption on concurrent writes. Always use `homeassistant.helpers.storage.Store` for schedule/room/person data.

---

## Pre-HACS Publication Checklist

- [ ] `async_unload_entry` cancels all listeners and scheduled callbacks
- [ ] All entities have `unique_id` and `_attr_has_entity_name = True`
- [ ] `manifest.json` has `version`, `iot_class: local_push`, `config_flow: true`, `requirements: []`
- [ ] `hacs.json` present with `zip_release: true`
- [ ] `strings.json` and `translations/en.json` present for all config flow strings
- [ ] GitHub Actions runs `hassfest` and `HACS` action on every PR
- [ ] No blocking I/O anywhere in async functions
- [ ] No `git+https` requirements

---

## Open Questions

- `async_track_point_in_time` has an open community report about reliability for exact-second scheduling. May need `async_track_time_change` (fires on HH:MM:SS match) instead to avoid accumulating drift. Warrants a prototype during the scheduler phase.
- Whether `embed_iframe: true` is required for the frontend panel depends on the JS framework. Lit (HA-native) does not require iframe. Decision must precede frontend phase.
