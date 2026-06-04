---
slug: refactor-async-evaluate
date: "2026-05-31"
status: in-progress
---

# Refactor async_evaluate

Decompose the 170-line `async_evaluate` method in `coordinator.py` into an
orchestrator that delegates to three focused private helpers.

## Goal

`async_evaluate` becomes a readable ~30-line orchestrator; all logic moves into
purpose-named helpers with clear signatures.

## File

`custom_components/climate_manager/coordinator.py`

## Tasks

### T-01 — Extract `_compute_desired_temps`

Extract PASS 1 (lines ~144–211) into:

```python
def _compute_desired_temps(
    self,
    config: dict,
    rooms: dict[str, list[str]],
    period_temperatures: dict[str, float],
    now: datetime,
) -> tuple[dict[str, float], dict[str, str], set[str], set[str]]:
```

Returns `(desired_temps, room_periods, frost_locked_rooms, mode_off_rooms)`.
No behavior change — pure extraction.

### T-02 — Extract `_apply_presence_overrides`

Extract PASS 2 (lines ~213–256) into:

```python
def _apply_presence_overrides(
    self,
    config: dict,
    rooms: dict[str, list[str]],
    desired_temps: dict[str, float],
    room_periods: dict[str, str],
    frost_locked_rooms: set[str],
    period_temperatures: dict[str, float],
    now: datetime,
) -> None:
```

Mutates `desired_temps` and `room_periods` in place.
`present_locked_rooms` stays internal to this method.

### T-03 — Extract `_push_temperatures`

Extract the push-pass `asyncio.gather` block (lines ~269–287) into:

```python
async def _push_temperatures(
    self,
    rooms: dict[str, list[str]],
    desired_temps: dict[str, float],
    mode_off_rooms: set[str],
) -> None:
```

### T-04 — Slim down `async_evaluate`

Replace extracted bodies with calls to the three new helpers.
Final `async_evaluate` body: setup → `_compute_desired_temps` → 
`_apply_presence_overrides` → update state fields →
`_push_temperatures` → fire event → `_async_calibrate`.

### T-05 — Run tests

```bash
make test
```

All existing tests must pass unchanged.

### T-06 — Commit

```bash
make lint
git add custom_components/climate_manager/coordinator.py
git commit -m "refactor(coordinator): decompose async_evaluate into focused helpers"
```
