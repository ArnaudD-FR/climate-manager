---
phase: 05-zone-crud-evaluation-engine
fixed_at: 2026-05-27T00:00:00Z
review_path: .planning/phases/05-zone-crud-evaluation-engine/05-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-27 **Source review:**
.planning/phases/05-zone-crud-evaluation-engine/05-REVIEW.md **Iteration:** 1

**Summary:**

- Findings in scope: 5 (CR-01, CR-02, WR-01, WR-02, WR-03)
- Fixed: 5
- Skipped: 0

Info findings IN-01 and IN-02 were out of scope for this run (fix_scope:
critical_warning).

## Fixed Issues

### CR-01: `validate_zone_assignment` prevents multiple rooms per zone

**Files modified:** `custom_components/climate_manager/storage.py` **Commit:**
f489ad5 **Applied fix:** Removed the `seen_zone_ids` set and the check that
raised `ValueError` when a `zone_id` appeared on more than one room. Updated the
docstring to explain that ZONE-04 is structurally guaranteed by the rooms dict
being keyed by `area_id`. The valid checks (unknown `zone_id` reference,
explicit `null` rejection) are preserved.

---

### CR-02: `_build_status_payload` emits temperature and humidity as strings

**Files modified:** `custom_components/climate_manager/coordinator.py`
**Commit:** dbd505a **Applied fix:** Added `float()` conversion with
`try/except (ValueError, TypeError)` around both `sensor_state.state`
assignments in `_build_status_payload`, matching the pattern already used in
`ws_get_status`. Temperature and humidity are now consistently emitted as floats
in both push events and request/response.

---

### WR-01: Zone write handlers mutate runtime_config before async_save with no rollback

**Files modified:** `custom_components/climate_manager/websocket.py` **Commit:**
932c472 **Applied fix:** Added `try/except Exception` blocks with
`copy.deepcopy` snapshot-and-restore rollback to all five affected handlers:

- `ws_create_zone`: snapshots `zones`, restores on failure
- `ws_rename_zone`: snapshots `default_zone_name` (for "default" branch) or
  `zones` (for custom zone branch), restores on failure
- `ws_set_zone_mode`: snapshots `zones`, restores on failure
- `ws_set_zone_time_program`: snapshots `zones`, restores on failure
- `ws_reset_zone_time_program`: snapshots `zones`, restores on failure

---

### WR-02: Variable name `entry` in `ws_get_config` generator shadows factory parameter

**Files modified:** `custom_components/climate_manager/websocket.py` **Commit:**
ec57e66 **Applied fix:** Renamed the generator iteration variable from `entry`
to `reg_entry` in both the `for` clause and the `if` filter expression. The
outer `entry` (ClimateManagerConfigEntry) reference on the following line is now
unambiguous.

---

### WR-03: `ws_set_zone_time_program` validates program before checking zone existence

**Files modified:** `custom_components/climate_manager/websocket.py` **Commit:**
6125ed0 **Applied fix:** Moved `runtime_config` access and the zone existence
check (`zone_id not in zones`) to run before `validate_daily_program`. The
program validation still runs before any mutation, preserving Pitfall 6 /
T-05-08 safety. Updated the docstring to reflect the new order and the
rationale.

---

_Fixed: 2026-05-27_ _Fixer: Claude (gsd-code-fixer)_ _Iteration: 1_
