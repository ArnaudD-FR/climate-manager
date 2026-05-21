---
quick_id: 260521-gck
slug: parallel-trv-push-commit
description: Commit parallel TRV push fix — coordinator.py now uses asyncio.gather to push all TRVs concurrently instead of sequentially, eliminating the ~10s delay on mode changes
date: 2026-05-21
must_haves:
  truths:
    - coordinator.py imports asyncio
    - _push_safely helper method exists in ClimateManagerCoordinator
    - MODE_OFF block uses asyncio.gather instead of sequential await loop
    - _evaluate_time_program collects pushes list then gathers them
    - _evaluate_time_program_presences Step 4 uses asyncio.gather
  artifacts:
    - custom_components/climate_manager/coordinator.py
---

# Quick Task 260521-gck: Commit Parallel TRV Push Fix

## Goal

Commit the already-implemented parallel TRV push fix to `coordinator.py`. The change replaces sequential `await` loops over TRVs with `asyncio.gather`, eliminating the ~10s cumulative delay when multiple TRVs are updated after a mode change.

## Context

The fix was implemented during the previous conversation turn but interrupted before deployment/commit. The change is already in the working tree. This task just commits it atomically.

## Change Summary

- Added `import asyncio` at top of coordinator.py
- Added `_push_safely(entity_id, desired_temp, context)` helper that wraps `_push_if_changed` with exception logging
- `MODE_OFF` block: replaced sequential loop with `asyncio.gather`
- `_evaluate_time_program`: collect pushes list first, then `asyncio.gather` all at once
- `_evaluate_time_program_presences` Step 4: replaced sequential loop with `asyncio.gather`

## Tasks

### Task 1: Commit coordinator.py parallel push fix

**Files:** `custom_components/climate_manager/coordinator.py`

**Action:** Stage only `coordinator.py` and commit with a descriptive message explaining the perf fix.

**Verify:**
- `import asyncio` is present
- `_push_safely` method exists
- `asyncio.gather` appears in MODE_OFF, _evaluate_time_program, and _evaluate_time_program_presences

**Done:** Commit hash recorded in SUMMARY.md
