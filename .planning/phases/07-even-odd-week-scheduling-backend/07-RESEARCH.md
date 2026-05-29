# Phase 7: Even/Odd Week Scheduling — Backend - Research

**Researched:** 2026-05-29
**Domain:** Python schedule evaluation, HA WebSocket handler, sparse storage
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Backend auto-seeds on type switch. When `set_person_config` receives
  `schedule_type: "even_odd"` and the person currently has no `schedule_even` in
  storage, the handler deep-copies `person_config.get("schedule", {})` into both
  `schedule_even` and `schedule_odd` before the sparse-merge.
- **D-02:** On revert (even_odd → single), `schedule_even` and `schedule_odd` are
  preserved silently in storage. `schedule` remains unchanged.
- **D-03:** Extend `set_person_config` only. No new WS command.
- **D-04:** `get_config` already returns the full `persons` dict — no read-path
  handler changes needed.
- **D-05:** No STORAGE_VERSION bump. Absent `schedule_type` defaults to `"single"`
  at read time (zero-migration additive extension).

### Claude's Discretion

- `resolve_presence()` modification: add schedule-selection block before the
  existing `schedule = person_config.get("schedule", {})` line. Compute
  `week_parity = now.date().isocalendar().week % 2`. If
  `schedule_type == "even_odd"`: select `schedule_even` (even week, parity 0) or
  `schedule_odd` (odd week, parity 1). Otherwise use `schedule` (default).
- Auto-seeding guard: if `schedule_type == "even_odd"` is incoming AND the stored
  `schedule_even` is already set, do NOT overwrite it.
- `const.py` persons sub-schema comment: document `schedule_type`, `schedule_even`,
  `schedule_odd`.

### Deferred Ideas (OUT OF SCOPE)

- UI week-switcher toggle (Phase 8)
- Any new WebSocket commands
- STORAGE_VERSION bump
- TRV calibration (Phase 9)
- Pronote scheduling source, multi-language support, boiler demand control
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID       | Description                                                                                          | Research Support                                                                  |
|----------|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| SCHED-01 | User can set a person's schedule type to "single" or "even/odd"                                      | `set_person_config` sparse-merge accepts new `schedule_type` field                |
| SCHED-02 | Backend evaluator selects correct schedule based on ISO week parity at evaluation time               | `resolve_presence()` extended with week-parity branch; stdlib `isocalendar().week`|
| SCHED-03 | Storage schema gains `schedule_type`, `schedule_even`, `schedule_odd`; existing persons unaffected   | Additive fields; absent `schedule_type` defaults to `"single"` at read time      |
| SCHED-05 | Switching from "single" to "even/odd" seeds both week schedules from existing `schedule`             | Auto-seed in `ws_set_person_config` before sparse-merge; deepcopy required        |
| SCHED-06 | Switching back from "even/odd" to "single" preserves `schedule` unchanged                           | `schedule` key untouched by any handler; sparse-merge never overwrites it         |
</phase_requirements>

---

## Summary

Phase 7 is a tightly-scoped, pure-Python backend extension. Every change is
contained in three files: `schedule.py` (evaluator), `websocket.py` (seeding
logic), and `const.py` (comment/documentation). A TypeScript type stub in
`frontend/src/types.ts` is also required as a cheap forward-compatibility step
for Phase 8.

The core algorithm is simple: `now.date().isocalendar().week % 2 == 0` means
even week (use `schedule_even`); `== 1` means odd week (use `schedule_odd`).
The rest of `resolve_presence()` is unchanged — the new block is inserted before
the existing `schedule = person_config.get("schedule", {})` line and falls
through to that line when `schedule_type` is absent or `"single"`.

The seeding logic in `ws_set_person_config` is the only non-trivial decision
surface: it must read the current person dict before the sparse-merge, check
whether `schedule_even` is already present, and deep-copy `schedule` into both
`schedule_even` and `schedule_odd` only when the key is absent. The existing
`copy` import in `websocket.py` covers this.

**Primary recommendation:** Three-file Python change + one TypeScript type stub.
No new WS commands, no migration, no schema version bump. All changes are purely
additive over the v1.1 storage model.

---

## Architectural Responsibility Map

| Capability                      | Primary Tier | Secondary Tier | Rationale                                          |
|---------------------------------|-------------|----------------|----------------------------------------------------|
| Week parity selection           | Backend      | —              | Pure datetime computation; no HA state needed      |
| Schedule seeding (single→even_odd) | Backend   | —              | Reads stored person dict; must run before merge    |
| Schedule storage (3 new fields) | Backend store | —             | Additive to existing sparse-merge pattern          |
| TypeScript type stub            | Frontend types | —             | Cheap forward-compatibility for Phase 8            |
| Week-switcher UI                | Frontend     | —              | Out of scope (Phase 8)                             |

---

## Standard Stack

No new packages. This phase uses only:

- **Python 3.12+ stdlib**: `datetime.date.isocalendar().week` — available since
  Python 3.9 via the named-tuple return. `[VERIFIED: Python docs]`
- **`copy.deepcopy`**: already imported in `websocket.py` (line 7). `[VERIFIED: codebase]`

### Package Legitimacy Audit

No external packages are installed in this phase. This section is not
applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
Frontend panel (Phase 8 — out of scope for Phase 7)
        |
        | set_person_config {schedule_type: "even_odd"}
        v
ws_set_person_config (websocket.py)
  ├─ read current person dict from runtime_config["persons"][person_id]
  ├─ [NEW] if schedule_type == "even_odd" and "schedule_even" not in current:
  │       seed payload["schedule_even"] = deepcopy(current.get("schedule", {}))
  │       seed payload["schedule_odd"]  = deepcopy(current.get("schedule", {}))
  ├─ sparse-merge payload into runtime_config["persons"][person_id]
  ├─ store.async_save(runtime_config)
  └─ coordinator.async_evaluate() [background]
        |
        | resolve_presence(person_config, now)
        v
schedule.py :: resolve_presence()
  ├─ mode == force_present → True
  ├─ mode == force_absent  → False
  └─ mode == "scheduled" (automatic)
        ├─ [NEW] schedule_type = person_config.get("schedule_type", "single")
        ├─ [NEW] if schedule_type == "even_odd":
        │       week_parity = now.date().isocalendar().week % 2
        │       schedule = person_config.get(
        │           "schedule_even" if week_parity == 0 else "schedule_odd", {}
        │       )
        └─ [EXISTING] else: schedule = person_config.get("schedule", {})
              → day lookup → period walk → True/False
```

### Recommended Project Structure

No new files or directories. Changes are in-place modifications.

```
custom_components/climate_manager/
├── schedule.py      ← resolve_presence() extended (primary change)
├── websocket.py     ← _make_ws_set_person_config seeding logic (secondary change)
└── const.py         ← persons sub-schema comment updated (doc only)
frontend/src/
└── types.ts         ← PersonConfig interface gains 3 optional fields
tests/
├── test_schedule.py ← new even/odd resolve_presence tests
└── test_coordinator.py ← new presence-with-even_odd coordinator tests
```

### Pattern 1: ISO Week Parity Selection in `resolve_presence()`

**What:** A single block inserted before the existing schedule lookup.
**When to use:** Always, in the `PRESENCE_AUTOMATIC` branch.

```python
# Source: codebase analysis + Python 3.9+ isocalendar() named-tuple
# Insert BEFORE: schedule = person_config.get("schedule", {})

schedule_type = person_config.get("schedule_type", "single")
if schedule_type == "even_odd":
    week_parity = now.date().isocalendar().week % 2
    schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
    schedule = person_config.get(schedule_key, {})
else:
    schedule = person_config.get("schedule", {})
```

The rest of the function body (`day_name`, `periods`, period-walk loop) is
unchanged.

### Pattern 2: Auto-Seeding in `ws_set_person_config`

**What:** Read the existing stored person dict, check for `schedule_even`, inject
seeds into the incoming `config` payload before the sparse-merge.
**When to use:** When the incoming `config` contains `schedule_type == "even_odd"`.

```python
# Source: codebase analysis — matches existing deepcopy pattern in websocket.py
# Insert BEFORE the setdefault(...).update(msg["config"]) line

incoming = msg["config"]
if incoming.get("schedule_type") == "even_odd":
    current_person = (
        entry.runtime_data.runtime_config
        .get("persons", {})
        .get(msg["person_id"], {})
    )
    if "schedule_even" not in current_person:
        existing_schedule = copy.deepcopy(
            current_person.get("schedule", {})
        )
        incoming.setdefault("schedule_even", existing_schedule)
        incoming.setdefault("schedule_odd", copy.deepcopy(
            current_person.get("schedule", {})
        ))
```

`copy` is already imported at the top of `websocket.py` (line 7). `[VERIFIED: codebase]`

### Pattern 3: TypeScript Type Extension

**What:** Add three optional fields to `PersonConfig` in `frontend/src/types.ts`.

```typescript
// Source: types.ts PersonConfig interface (line 42-46)
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

`DailyProgram` is already defined in `types.ts` (line 21-24) as
`Record<"mon"|"tue"|"wed"|"thu"|"fri"|"sat"|"sun", Period[]>`. `[VERIFIED: codebase]`

### Anti-Patterns to Avoid

- **Seeding at load time (storage.py):** Do not add seeding logic to
  `async_load()`. Seeding belongs in the WS handler at the moment of type
  switch, not at every load. Storage should remain a pure passthrough for new
  additive fields.
- **Overwriting an existing `schedule_even`:** The guard `"schedule_even" not in
  current_person` must use `not in` (key-absence check), NOT truthiness (`if not
  current_person.get("schedule_even")`). An explicitly empty schedule `{}` must
  not be overwritten.
- **Mutating `msg["config"]` directly without care:** The seeding logic modifies
  `incoming` (a reference to `msg["config"]`). This is fine because the dict is
  not used after the handler returns, but document it clearly.
- **Using `.isocalendar()[1]` instead of `.isocalendar().week`:** The
  named-tuple attribute access (`.week`) is cleaner and available from Python
  3.9+. Both forms work in Python 3.12+, but prefer the named attribute.
- **Bumping STORAGE_VERSION:** Absent fields default at read time — no migration
  is needed. A version bump would require writing a migration function in
  `storage.py` and is explicitly locked out by D-05.

---

## Don't Hand-Roll

| Problem                          | Don't Build             | Use Instead                                    | Why                                    |
|----------------------------------|-------------------------|------------------------------------------------|----------------------------------------|
| ISO week number                  | Custom week calculation | `datetime.date.isocalendar().week`             | Stdlib; handles ISO 8601 edge cases    |
| Deep copy of schedule dict       | Manual dict recursion   | `copy.deepcopy()`                              | Already imported; handles nested lists |
| Person config persistence        | Direct file I/O         | `store.async_save(runtime_config)`             | Existing pattern; never bypass Store   |

---

## Common Pitfalls

### Pitfall 1: Overwriting User-Edited `schedule_even`

**What goes wrong:** Seeding fires every time `schedule_type: "even_odd"` is
sent, even if the user has already edited `schedule_even` independently.
**Why it happens:** Not checking whether the key already exists before seeding.
**How to avoid:** Guard with `"schedule_even" not in current_person` (key-absence,
not truthiness). An existing empty `{}` schedule must not be overwritten.
**Warning signs:** User edits even-week schedule, presses save for an unrelated
field (e.g., `room_ids`), even-week schedule resets to the single schedule.

### Pitfall 2: Shared Reference After `deepcopy`

**What goes wrong:** `schedule_even` and `schedule_odd` end up pointing at the
same dict object, so editing one silently edits the other.
**Why it happens:** Using a single `deepcopy` result for both fields.
**How to avoid:** Call `copy.deepcopy()` twice — once for `schedule_even`, once
for `schedule_odd`. (See Pattern 2 code above.)
**Warning signs:** Editing the even-week schedule also changes the odd-week
schedule unexpectedly.

### Pitfall 3: `isocalendar()` on `datetime` vs. `date`

**What goes wrong:** Calling `now.isocalendar().week` directly on a `datetime`
object — this works in Python 3.9+ because `datetime` inherits `isocalendar()`
from `date`. However, the CONTEXT.md specifies `now.date().isocalendar().week`
for clarity, and `schedule.py` already uses `now.weekday()` (from `datetime`).
**How to avoid:** Use `now.date().isocalendar().week` as specified in
`## Claude's Discretion`. Both are equivalent, but the explicit `.date()` call
makes the intent clear and matches the CONTEXT.md specification.

### Pitfall 4: `resolve_presence` Called with `mode == "ha"`

**What goes wrong:** The `mode == "ha"` branch is handled in
`coordinator._compute_present_persons()` before `resolve_presence()` is called
— HA-mode persons never reach `resolve_presence()`. The new even/odd block is
inside `resolve_presence()`, so it is correctly skipped for HA-mode persons.
**How to avoid:** No action needed — the coordinator correctly gates HA-mode
persons before calling `resolve_presence()`. Confirm in tests that HA-mode
persons are unaffected.

### Pitfall 5: Coordinator Calls `resolve_presence()` in Two Places

**What goes wrong:** Updating only one call site in the coordinator and missing
the other.
**Why it happens:** `resolve_presence()` is called from both:
  1. `async_evaluate()` → PASS 2 (line ~206, presence override loop)
  2. `_compute_present_persons()` (line ~328, status reporting)
**How to avoid:** There is no coordinator change needed — the signature of
`resolve_presence(person_config, now)` is unchanged. The new fields are read
from `person_config` inside the function. Both call sites automatically benefit.

---

## Code Examples

### Exact Insertion Point in `resolve_presence()`

```python
# schedule.py — resolve_presence() — lines 117-158 CURRENT:
#   mode = person_config.get("mode", PRESENCE_AUTOMATIC)
#   ...
#   # Automatic: evaluate periodic schedule (per-day dict, D-01)
#   schedule = person_config.get("schedule", {})       ← REPLACE THIS LINE
#   day_name = WEEKDAY_TO_DAY[now.weekday()]
#   periods = schedule.get(day_name, [])

# REPLACEMENT:
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
```

### Exact Insertion Point in `ws_set_person_config`

```python
# websocket.py — _make_ws_set_person_config — CURRENT inner function body:
#   async def ws_set_person_config(...):
#       (
#           entry.runtime_data.runtime_config.setdefault("persons", {})
#           .setdefault(msg["person_id"], {})
#           .update(msg["config"])                       ← BEFORE THIS
#       )
#       await entry.runtime_data.store.async_save(...)

# INSERT BEFORE the setdefault chain:
        # SCHED-05: auto-seed schedule_even/schedule_odd when switching to even_odd
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

### `const.py` Comment Update (persons sub-schema, lines 130-145)

```python
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",   # "scheduled" | "force_present" | "force_absent" | "ha"
#       "room_ids": ["<area_id>", ...],
#       "schedule": {                # used when schedule_type == "single" (default)
#         "mon": [{"start": "HH:MM", "state": "present"|"absent"}, ...],
#         ...
#       },
#       "schedule_type": "single" | "even_odd",  # SCHED-01/03; absent = "single"
#       "schedule_even": { ... },   # SCHED-03; same structure as schedule;
#                                   # used during even ISO weeks (parity == 0)
#       "schedule_odd":  { ... },   # SCHED-03; same structure as schedule;
#                                   # used during odd ISO weeks (parity == 1)
#     }
#   }
```

---

## State of the Art

| Old Approach         | Current Approach                  | When Changed | Impact                          |
|----------------------|-----------------------------------|--------------|---------------------------------|
| Single `schedule` key | `schedule_type` + optional pair  | Phase 7      | Backward-compat: absent = single |

**Deprecated/outdated:** Nothing deprecated. This is a pure additive extension.

---

## Assumptions Log

All claims in this research were verified against the codebase or Python stdlib
documentation. No `[ASSUMED]` tags present.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**This table is empty:** All claims were verified or cited.

---

## Open Questions

1. **`ws_set_person_config` docstring update**
   - What we know: The existing docstring references only `T-03-09`.
   - What's unclear: Whether to add a new tag (e.g., `T-07-01`) referencing
     SCHED-05.
   - Recommendation: Add an inline comment referencing SCHED-05 rather than a
     formal tag — keeping the pattern consistent with `set_room_config` which
     also uses inline `# T-03-09` comments.

2. **Test for revert (even_odd → single) preserving `schedule_even`/`schedule_odd`**
   - What we know: D-02 says the fields are silently preserved in storage.
   - What's unclear: Whether a test should explicitly verify the preserved fields
     remain in the stored dict after reverting.
   - Recommendation: Yes — add one test asserting that after sending
     `{schedule_type: "single"}`, the stored person still has `schedule_even` and
     `schedule_odd` keys.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — all changes are Python stdlib +
existing HA APIs already in use).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-homeassistant-custom-component (latest) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `make test` |
| Full suite command | `make test` |

Baseline: 127 passed, 1 pre-existing failure (`test_phase06_acceptance.py::test_main_tab_overview_label`) unrelated to Phase 7. `[VERIFIED: codebase — make test run]`

### Phase Requirements → Test Map

| Req ID   | Behavior                                               | Test Type | Automated Command                        | File Exists? |
|----------|--------------------------------------------------------|-----------|------------------------------------------|--------------|
| SCHED-01 | `schedule_type` field accepted by `set_person_config` | unit      | `make test` (test_websocket.py)          | ✅ Wave 0    |
| SCHED-02 | Even week → `schedule_even`; odd week → `schedule_odd`| unit      | `make test` (test_schedule.py)           | ✅ (extend)  |
| SCHED-02 | Backward compat: absent `schedule_type` → "single"    | unit      | `make test` (test_schedule.py)           | ✅ (extend)  |
| SCHED-03 | Existing person without new fields unaffected          | unit      | `make test` (test_schedule.py)           | ✅ (extend)  |
| SCHED-05 | Single→even_odd seeds both schedules from `schedule`  | unit      | `make test` (test_websocket.py)          | ✅ Wave 0    |
| SCHED-05 | Seeding guard: `schedule_even` already set → no overwrite | unit  | `make test` (test_websocket.py)          | ✅ Wave 0    |
| SCHED-06 | even_odd→single preserves `schedule_even`/`odd` in storage | unit | `make test` (test_websocket.py)          | ✅ Wave 0    |

### Specific Test Cases to Add

**In `tests/test_schedule.py`** (pure-Python, no hass fixture):

```python
# T-07-S1: even ISO week uses schedule_even
def test_resolve_presence_even_odd_even_week_uses_schedule_even():
    # 2026-01-05 (Mon) = ISO week 2, parity 0 (even) → schedule_even
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "even_odd",
        "schedule_even": {  # present Mon 08:00-22:00
            day: [{"start": "08:00", "state": "present"}] if day == "mon" else []
            for day in ALL_DAYS
        },
        "schedule_odd": {   # always absent
            day: [{"start": "00:00", "state": "absent"}] for day in ALL_DAYS
        },
    }
    assert resolve_presence(config, now) is True  # even week → schedule_even → present

# T-07-S2: odd ISO week uses schedule_odd
def test_resolve_presence_even_odd_odd_week_uses_schedule_odd():
    # 2026-01-12 (Mon) = ISO week 3, parity 1 (odd) → schedule_odd
    now = datetime.datetime(2026, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)
    # ... schedule_even is always-present, schedule_odd is always-absent
    assert resolve_presence(config, now) is False  # odd week → schedule_odd → absent

# T-07-S3: absent schedule_type defaults to "single" (backward compat)
def test_resolve_presence_no_schedule_type_uses_schedule():
    config = {"mode": PRESENCE_AUTOMATIC, "schedule": PERSON_SCHEDULE}
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True  # uses schedule (single mode)

# T-07-S4: schedule_type="single" explicit — same as absent
def test_resolve_presence_explicit_single_uses_schedule():
    config = {
        "mode": PRESENCE_AUTOMATIC,
        "schedule_type": "single",
        "schedule": PERSON_SCHEDULE,
    }
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    assert resolve_presence(config, now) is True

# T-07-S5: even_odd with no schedule_even → empty schedule → absent
def test_resolve_presence_even_odd_missing_week_schedule_returns_false():
    now = datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc)
    config = {"mode": PRESENCE_AUTOMATIC, "schedule_type": "even_odd"}
    # no schedule_even → .get("schedule_even", {}) → {} → absent
    assert resolve_presence(config, now) is False
```

**In `tests/test_websocket.py`** (requires hass fixture):

```
T-07-W1: set_person_config with schedule_type="even_odd" seeds schedule_even
         and schedule_odd from existing schedule (SCHED-05)
T-07-W2: seed guard — second set_person_config with schedule_type="even_odd"
         does NOT overwrite an already-set schedule_even (Pitfall 1)
T-07-W3: set_person_config with schedule_type="single" does NOT touch
         schedule_even / schedule_odd (D-02)
T-07-W4: after even_odd→single revert, schedule_even and schedule_odd remain
         in the stored person dict (D-02 preservation)
```

### Sampling Rate

- **Per task commit:** `make test`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green (127+ passed) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test functions in `tests/test_schedule.py` — covers SCHED-01..03
- [ ] New test functions in `tests/test_websocket.py` — covers SCHED-05, SCHED-06

*(Existing test infrastructure is fully in place; only new test functions are
needed, not new files or framework setup.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category     | Applies | Standard Control                                     |
|-------------------|---------|------------------------------------------------------|
| V2 Authentication | no      | WS auth handled by HA core (T-03-06)                 |
| V3 Session        | no      | HA session management                                |
| V4 Access Control | no      | Panel only accessible to HA authenticated users      |
| V5 Input Validation | yes   | `schedule_type` value not voluptuous-validated       |
| V6 Cryptography   | no      | No crypto in this phase                              |

### Input Validation Gap

The existing `set_person_config` handler accepts `config: dict` with no schema
validation on its contents (only `vol.Required("config"): dict`). This is an
existing pattern throughout the codebase — the handler trusts that the
authenticated panel sends valid data. For Phase 7, `schedule_type` will be an
unvalidated string key.

**Risk:** Low. Only authenticated HA users can reach this WS endpoint (T-03-06).
A malformed `schedule_type` value (anything other than `"single"` or `"even_odd"`)
will cause `resolve_presence()` to fall through to the `else` branch (uses
`schedule`) because the `if schedule_type == "even_odd"` check will simply be
False. No crash, no data corruption.

**Recommendation:** Optionally add a guard in `resolve_presence()` for
unknown values — fall through to `"single"` behavior. No voluptuous schema
change required for the existing handler pattern.

---

## Sources

### Primary (HIGH confidence)

- Codebase — `custom_components/climate_manager/schedule.py` — `resolve_presence()` lines 117-158
- Codebase — `custom_components/climate_manager/websocket.py` — `_make_ws_set_person_config` lines 441-472
- Codebase — `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG` persons schema lines 130-151
- Codebase — `custom_components/climate_manager/storage.py` — sparse-merge pattern lines 104-121
- Codebase — `custom_components/climate_manager/coordinator.py` — two `resolve_presence()` call sites
- Codebase — `frontend/src/types.ts` — `PersonConfig` interface lines 42-46; `DailyProgram` lines 21-24
- Python stdlib — `datetime.date.isocalendar()` named-tuple `.week` attribute — Python 3.9+

### Secondary (MEDIUM confidence)

- `.planning/phases/07-even-odd-week-scheduling-backend/07-CONTEXT.md` — all locked decisions
- `.planning/REQUIREMENTS.md` — SCHED-01..06 definitions
- `.planning/ROADMAP.md` — Phase 7 success criteria

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — pure stdlib + existing patterns, no new dependencies
- Architecture: HIGH — change points are exact and verified in codebase
- Pitfalls: HIGH — derived from direct code inspection of the seeding and
  evaluation paths
- Test patterns: HIGH — existing test files read and patterns confirmed

**Research date:** 2026-05-29
**Valid until:** Stable (no external dependencies; valid until schedule.py or
websocket.py are otherwise refactored)
