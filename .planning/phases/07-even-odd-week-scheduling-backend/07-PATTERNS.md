# Phase 7: Even/Odd Week Scheduling — Backend - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 6
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/climate_manager/schedule.py` | utility / evaluator | transform | `schedule.py` itself (existing `evaluate_schedule`) | exact |
| `custom_components/climate_manager/websocket.py` | service / handler | request-response | `websocket.py` `_make_ws_set_room_config` factory (lines 395–438) | exact |
| `custom_components/climate_manager/const.py` | config | — | `const.py` persons sub-schema comment (lines 130–151) | exact (doc only) |
| `frontend/src/types.ts` | model / type stub | — | `types.ts` `RoomConfig` interface (lines 27–39) | role-match |
| `tests/test_schedule.py` | test | — | `test_schedule.py` `resolve_presence` block (lines 257–317) | exact |
| `tests/test_websocket.py` | test | — | `test_websocket.py` `set_person_config` / `set_global_mode` tests | role-match |

---

## Pattern Assignments

### `custom_components/climate_manager/schedule.py` — `resolve_presence()` extension

**Analog:** `schedule.py` lines 117–158 (the existing `resolve_presence` function
and `evaluate_schedule` at lines 79–114 for the period-walk pattern).

**Imports pattern** (lines 1–36):
```python
# SPDX-License-Identifier: MIT
import datetime
import logging

from .const import (
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT,
)
```
No new imports needed — `datetime` is already in scope.

**Core pattern — existing automatic branch** (lines 138–158):
```python
# Automatic: evaluate periodic schedule (per-day dict, D-01)
schedule = person_config.get("schedule", {})      # ← REPLACE this line only
day_name = WEEKDAY_TO_DAY[now.weekday()]
periods = schedule.get(day_name, [])
if not periods:
    return False  # PERSON-05: no periods today → absent
```

**Replacement block to insert before the day-lookup:**
```python
# Automatic: evaluate periodic schedule (per-day dict, D-01)
# SCHED-02: select the correct week schedule based on ISO week parity
schedule_type = person_config.get("schedule_type", "single")
if schedule_type == "even_odd":
    week_parity = now.date().isocalendar().week % 2
    schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
    schedule = person_config.get(schedule_key, {})
else:
    schedule = person_config.get("schedule", {})
day_name = WEEKDAY_TO_DAY[now.weekday()]
periods = schedule.get(day_name, [])
if not periods:
    return False  # PERSON-05: no periods today → absent
```

**Style rules observed in this file:**
- Pure Python — no HA imports anywhere.
- `now.date().isocalendar().week` is preferred over `now.isocalendar().week`
  (explicit `.date()` call, matching CONTEXT.md Claude's Discretion).
- All module-level constants use `ALL_CAPS`; local variables use `snake_case`.
- Comment lines begin with `# ` and reference requirement IDs (e.g., `PERSON-05`).
- 4-space indent, max 80 chars per line (`.editorconfig`).

---

### `custom_components/climate_manager/websocket.py` — `_make_ws_set_person_config` seeding

**Analog:** `websocket.py` `_make_ws_set_person_config` factory, lines 441–472
(the function that gets extended).

**Imports pattern** (lines 1–7, verified by RESEARCH.md):
```python
# copy is already imported at line 7 — no new import needed.
import copy
```

**Existing core pattern** (lines 460–470):
```python
async def ws_set_person_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Sparse-merge config into persons[person_id] without wiping other persons.

    T-03-09: same setdefault + update pattern as set_room_config.
    """
    (
        entry.runtime_data.runtime_config.setdefault("persons", {})
        .setdefault(msg["person_id"], {})
        .update(msg["config"])
    )
    await entry.runtime_data.store.async_save(
        entry.runtime_data.runtime_config
    )
    connection.send_result(msg["id"], {"success": True})
    hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

**Seeding block to insert BEFORE the `setdefault` chain** (SCHED-05):
```python
# SCHED-05: auto-seed schedule_even/schedule_odd when switching to even_odd.
# Guard: only seed when schedule_even is not already in storage — an
# existing empty {} schedule must not be overwritten (key-absence, not
# truthiness — Pitfall 1 in RESEARCH.md).
incoming = msg["config"]
if incoming.get("schedule_type") == "even_odd":
    current_person = (
        entry.runtime_data.runtime_config
        .get("persons", {})
        .get(msg["person_id"], {})
    )
    if "schedule_even" not in current_person:
        incoming.setdefault(
            "schedule_even",
            copy.deepcopy(current_person.get("schedule", {})),
        )
        incoming.setdefault(
            "schedule_odd",
            copy.deepcopy(current_person.get("schedule", {})),
        )
```

**Write-then-evaluate pattern** (from `set_room_config` analog at lines 395–438):
```python
# All write handlers follow this exact sequence:
#   1. mutate runtime_config
#   2. store.async_save (await)
#   3. connection.send_result
#   4. coordinator.async_evaluate (background task, NOT awaited directly)
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

**Style rules observed in this file:**
- Factory function naming: `_make_ws_<command_name>` returns the inner handler.
- Docstring on the inner handler references requirement tags (e.g., `T-03-09`).
- Inline comments reference requirement IDs (e.g., `# SCHED-05`).
- `copy.deepcopy()` called once per destination — never share the same deepcopy
  result across two fields (Pitfall 2 in RESEARCH.md).
- `setdefault` is preferred over `if key not in dict: dict[key] = ...`.
- 4-space indent, max 80 chars per line.

---

### `custom_components/climate_manager/const.py` — persons sub-schema comment update

**Analog:** `const.py` persons sub-schema comment block, lines 130–151.

**Existing comment to extend** (lines 130–147):
```python
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",   # "scheduled" | "force_present" | "force_absent" | "ha"
#       "room_ids": ["<area_id>", ...],
#       "schedule": {
#         "mon": [{"start": "HH:MM", "state": "present"|"absent"}, ...],
#         "tue": [...],
#         ...
#         "sun": [...]
#       }
#     }
#   }
#   Empty dict = all persons at default (Automatic mode, no schedule, no rooms).
#   A person entry only appears if it has at least one non-default setting.
```

**Replacement with three new field docs** (SCHED-01, SCHED-03):
```python
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",   # "scheduled" | "force_present" | "force_absent" | "ha"
#       "room_ids": ["<area_id>", ...],
#       "schedule": {                # used when schedule_type == "single" (default)
#         "mon": [{"start": "HH:MM", "state": "present"|"absent"}, ...],
#         "tue": [...],
#         "wed": [...],
#         "thu": [...],
#         "fri": [...],
#         "sat": [...],
#         "sun": [...]
#       },
#       "schedule_type": "single" | "even_odd",  # SCHED-01/03; absent = "single"
#       "schedule_even": { ... },   # SCHED-03; same structure as schedule;
#                                   # used during even ISO weeks (parity == 0)
#       "schedule_odd":  { ... },   # SCHED-03; same structure as schedule;
#                                   # used during odd ISO weeks (parity == 1)
#     }
#   }
#   Empty dict = all persons at default (Automatic mode, no schedule, no rooms).
#   A person entry only appears if it has at least one non-default setting.
```

**Style rules observed in this file:**
- `copy` is imported at line 9 — already present, no addition needed.
- Comment-only change: no logic or constant additions in `const.py` for this phase.
- Inline comment alignment follows existing column style (space-pad to `#` at
  column ~7 inside the schema block).

---

### `frontend/src/types.ts` — `PersonConfig` interface extension

**Analog:** `types.ts` `PersonConfig` interface (lines 42–46) and `RoomConfig`
interface (lines 27–39) for the optional-field pattern.

**Existing `PersonConfig`** (lines 42–46):
```typescript
/** Per-person configuration stored in ClimateConfig.persons. */
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
}
```

**Existing `DailyProgram` type** (lines 21–24) — already the correct type for
the new fields:
```typescript
/** Seven-day program map keyed by lowercase day abbreviation. */
export type DailyProgram = Record<
  "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun",
  Period[]
>;
```

**Extended `PersonConfig` with three new optional fields** (SCHED-01, SCHED-03):
```typescript
/** Per-person configuration stored in ClimateConfig.persons. */
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
  // Phase 7: even/odd week scheduling (SCHED-01, SCHED-03)
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;
  schedule_odd?: DailyProgram;
}
```

**Style rules observed in this file:**
- All interface fields are optional (`?`) for sparse config objects.
- JSDoc comment above the interface, not inline with each field (except
  for non-obvious fields like `zone_id` which have an inline JSDoc).
- Phase-reference comment pattern: `// Phase N: description (REQ-ID)`.
- 2-space indent, max 80 chars per line (`.editorconfig`).
- No new imports needed — `DailyProgram` is already defined in the same file.

---

### `tests/test_schedule.py` — new `resolve_presence` test functions

**Analog:** `test_schedule.py` existing `resolve_presence` tests, lines 257–317.

**Test fixture pattern** (lines 83–115) — reuse `PERSON_SCHEDULE`:
```python
# Presence schedule: Mon–Fri present 08:00–22:00, absent otherwise; Sat–Sun absent
PERSON_SCHEDULE: dict = {
    "mon": [
        {"start": "00:00", "state": "absent"},
        {"start": "08:00", "state": "present"},
        {"start": "22:00", "state": "absent"},
    ],
    # ... (all 7 days)
}
```

**Existing test structure to follow** (lines 302–317):
```python
def test_resolve_presence_automatic_during_present_period():
    """PERSON-04: automatic mode, schedule says present at current time → True."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(
        2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc
    )  # Monday 10:00
    assert resolve_presence(config, now) is True
```

**New test functions to add** (T-07-S1 through T-07-S5):

New module-level fixtures needed (add alongside `PERSON_SCHEDULE`):
```python
# All-days-present schedule for even_odd tests
ALWAYS_PRESENT_SCHEDULE: dict = {
    day: [{"start": "00:00", "state": "present"}] for day in ALL_DAYS
}

# All-days-absent schedule for even_odd tests
ALWAYS_ABSENT_SCHEDULE: dict = {
    day: [{"start": "00:00", "state": "absent"}] for day in ALL_DAYS
}
```

Test bodies following the established pattern:
```python
# T-07-S1: even ISO week → schedule_even
def test_resolve_presence_even_odd_even_week_uses_schedule_even():
    """SCHED-02: ISO week 2 (2026-01-05, Mon) has parity 0 → even → schedule_even."""
    # 2026-01-05 = ISO week 2, parity 0 (even)
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert now.date().isocalendar().week % 2 == 0  # Sanity: even week
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "even_odd",
        "schedule_even": ALWAYS_PRESENT_SCHEDULE,
        "schedule_odd": ALWAYS_ABSENT_SCHEDULE,
    }
    assert resolve_presence(config, now) is True  # even week → present


# T-07-S2: odd ISO week → schedule_odd
def test_resolve_presence_even_odd_odd_week_uses_schedule_odd():
    """SCHED-02: ISO week 3 (2026-01-12, Mon) has parity 1 → odd → schedule_odd."""
    # 2026-01-12 = ISO week 3, parity 1 (odd)
    now = datetime.datetime(2026, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)
    assert now.date().isocalendar().week % 2 == 1  # Sanity: odd week
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "even_odd",
        "schedule_even": ALWAYS_PRESENT_SCHEDULE,
        "schedule_odd": ALWAYS_ABSENT_SCHEDULE,
    }
    assert resolve_presence(config, now) is False  # odd week → absent


# T-07-S3: absent schedule_type → falls back to "single" behavior
def test_resolve_presence_no_schedule_type_uses_schedule():
    """SCHED-03: absent schedule_type defaults to single — uses schedule key."""
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True


# T-07-S4: explicit schedule_type="single" → same as absent
def test_resolve_presence_explicit_single_uses_schedule():
    """SCHED-02: explicit schedule_type='single' selects schedule key."""
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "single",
        "schedule": PERSON_SCHEDULE,
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True


# T-07-S5: even_odd with missing week schedule → empty → absent
def test_resolve_presence_even_odd_missing_week_schedule_returns_false():
    """PERSON-05 + SCHED-02: even_odd with no schedule_even key → {} → absent."""
    # ISO week 2 → even → looks for schedule_even → not found → {} → absent
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    config = {"mode": PRESENCE_AUTOMATIC, "schedule_type": "even_odd"}
    # No schedule_even key at all → .get("schedule_even", {}) → no periods
    assert resolve_presence(config, now) is False
```

**Style rules observed:**
- No hass fixture — pure Python, `import datetime` only.
- `datetime.timezone.utc` always used for timezone-aware `now`.
- Inline sanity assertion with `assert now.weekday() == N` pattern (lines 127,
  170) — extend with `assert now.date().isocalendar().week % 2 == N`.
- Docstring: one-liner stating the requirement ID + expected behavior.
- File-level docstring module header references the new tests (update `Tests:`
  block at lines 5–8).

---

### `tests/test_websocket.py` — new `set_person_config` test functions

**Analog:** `test_websocket.py` `test_ws_set_global_mode_persists_and_evaluates`
(lines 69–85) and `test_ws_get_status_includes_present_person_count` (lines
135–175) for the state-seeding + WS send + assert pattern.

**Setup helper** (lines 30–39, reuse without modification):
```python
async def _setup_entry(hass) -> MockConfigEntry:
    """Helper: set up the integration entry and return it."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
```

**WS send-and-assert pattern** (lines 69–85):
```python
entry = await _setup_entry(hass)
client = await hass_ws_client()
await client.send_json_auto_id(
    {"type": f"{DOMAIN}/set_global_mode", "mode": MODE_OFF}
)
msg = await client.receive_json()
assert msg["success"] is True
assert msg["result"]["success"] is True
assert entry.runtime_data.runtime_config["global_mode"] == MODE_OFF
```

**State-seeding pattern** (lines 145–153, from `present_person_count` test):
```python
# Mutate runtime_config directly before sending the WS command
entry.runtime_data.runtime_config["persons"] = {
    "person.alice": {"room_ids": ["living_room"]},
}
```

**New test functions to add** (T-07-W1 through T-07-W4):
```python
# T-07-W1: single→even_odd seeds both schedule_even and schedule_odd (SCHED-05)
async def test_ws_set_person_config_seeds_even_odd_from_schedule(
    hass, hass_ws_client
):
    """SCHED-05: switching to even_odd seeds schedule_even and schedule_odd
    from the existing schedule when neither key is present in storage.
    """
    entry = await _setup_entry(hass)

    # Seed an existing single schedule for person.alice
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {"schedule": PERSON_SCHEDULE},
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/set_person_config",
        "person_id": "person.alice",
        "config": {"schedule_type": "even_odd"},
    })
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert stored["schedule_type"] == "even_odd"
    assert "schedule_even" in stored
    assert "schedule_odd" in stored
    # Seeded copies must equal the original schedule
    assert stored["schedule_even"] == PERSON_SCHEDULE
    assert stored["schedule_odd"] == PERSON_SCHEDULE
    # Seeded copies must be independent objects (Pitfall 2)
    assert stored["schedule_even"] is not stored["schedule_odd"]


# T-07-W2: seeding guard — second switch does not overwrite existing schedule_even
async def test_ws_set_person_config_does_not_overwrite_existing_schedule_even(
    hass, hass_ws_client
):
    """SCHED-05 guard: schedule_even already in storage → no overwrite."""
    entry = await _setup_entry(hass)

    custom_even = {"mon": [{"start": "06:00", "state": "present"}],
                   **{d: [] for d in ["tue", "wed", "thu", "fri", "sat", "sun"]}}
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {
            "schedule_type": "even_odd",
            "schedule_even": custom_even,
            "schedule_odd": {},
        }
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/set_person_config",
        "person_id": "person.alice",
        "config": {"schedule_type": "even_odd"},
    })
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    # schedule_even must remain the custom value (not reset)
    assert stored["schedule_even"] == custom_even


# T-07-W3: set_person_config with schedule_type="single" does not touch
#           schedule_even / schedule_odd (D-02)
async def test_ws_set_person_config_single_does_not_seed(hass, hass_ws_client):
    """D-02: schedule_type=single → no seeding, schedule_even/odd not added."""
    entry = await _setup_entry(hass)
    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {"schedule": PERSON_SCHEDULE},
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/set_person_config",
        "person_id": "person.alice",
        "config": {"schedule_type": "single"},
    })
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert "schedule_even" not in stored
    assert "schedule_odd" not in stored


# T-07-W4: after even_odd→single revert, schedule_even/odd preserved in storage (D-02)
async def test_ws_set_person_config_revert_preserves_week_schedules(
    hass, hass_ws_client
):
    """D-02: reverting to single preserves schedule_even and schedule_odd in storage."""
    entry = await _setup_entry(hass)

    entry.runtime_data.runtime_config["persons"] = {
        "person.alice": {
            "schedule_type": "even_odd",
            "schedule_even": PERSON_SCHEDULE,
            "schedule_odd": PERSON_SCHEDULE,
        }
    }

    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/set_person_config",
        "person_id": "person.alice",
        "config": {"schedule_type": "single"},
    })
    msg = await client.receive_json()

    assert msg["success"] is True
    stored = entry.runtime_data.runtime_config["persons"]["person.alice"]
    assert stored["schedule_type"] == "single"
    # D-02: week schedules silently preserved — user can switch back later
    assert "schedule_even" in stored
    assert "schedule_odd" in stored
```

**Imports to add** at the top of `test_websocket.py` (alongside existing imports):
```python
# Add PERSON_SCHEDULE fixture inline or import the constant from test_schedule.py.
# Prefer inline dict definition to keep the test file self-contained.
# Pattern: same PERSON_SCHEDULE dict used in test_schedule.py (lines 84–112).
```

**Style rules observed:**
- `async def test_*(hass, hass_ws_client)` signature — all WS tests are async.
- `_setup_entry(hass)` helper is always called first.
- `client = await hass_ws_client()` followed by `send_json_auto_id` + `receive_json`.
- Assert `msg["success"] is True` before asserting `runtime_config` state.
- 2-space indent inside JSON payloads passed to `send_json_auto_id`.
- Section separator comment blocks: `# ---------------------------------------------------------------------------`.
- 4-space Python indent, max 80 chars.

---

## Shared Patterns

### Sparse-merge write pattern (CRUD handler — all write WS commands)

**Source:** `websocket.py` lines 460–470 (`ws_set_person_config`), lines
395–438 (`ws_set_room_config`)

**Apply to:** Any new mutation in `set_person_config`

```python
# Pattern: mutate → save → send_result → background evaluate
(
    entry.runtime_data.runtime_config.setdefault("persons", {})
    .setdefault(msg["person_id"], {})
    .update(msg["config"])  # sparse-merge: only sent keys are overwritten
)
await entry.runtime_data.store.async_save(
    entry.runtime_data.runtime_config
)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

### Deep-copy isolation pattern

**Source:** `const.py` line 9 (`import copy`) and `websocket.py` line 7

**Apply to:** `websocket.py` seeding block and any place where two independent
copies of a mutable dict are needed.

```python
import copy
# Always call deepcopy twice for two separate destinations:
copy.deepcopy(source)   # for schedule_even
copy.deepcopy(source)   # for schedule_odd — must NOT reuse the first result
```

### `setdefault` key-absence guard pattern

**Source:** `websocket.py` lines 462–464 (the `setdefault` chain)

**Apply to:** Seeding guard in `ws_set_person_config` — key-absence check.

```python
# Use "key not in dict" (key-absence), NOT "not dict.get(key)" (truthiness).
# An empty {} schedule must NOT be overwritten.
if "schedule_even" not in current_person:
    incoming.setdefault("schedule_even", copy.deepcopy(...))
    incoming.setdefault("schedule_odd",  copy.deepcopy(...))
```

### Pure-Python constraint (`schedule.py`)

**Source:** `schedule.py` module docstring (line 3–4)

**Apply to:** All code added to `schedule.py`

```
# Pure Python — no Home Assistant imports.
# All functions accept datetime objects directly; callers supply dt_util.now().
```
Only `datetime`, `logging`, and `.const` imports are allowed. The new
`isocalendar().week` call is stdlib — no new import required.

### TypeScript optional-field interface pattern

**Source:** `types.ts` `RoomConfig` (lines 27–39) and `PersonConfig`
(lines 42–46)

**Apply to:** `PersonConfig` extension in `types.ts`

```typescript
// All config interface fields are optional (?) — sparse storage model.
// New fields are appended at the end of the interface, never interleaved.
// DailyProgram type is already in scope — no import needed.
```

---

## No Analog Found

All six files have close analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/`

**Files scanned:** 7 source files, 2 test files

**Pattern extraction date:** 2026-05-29
