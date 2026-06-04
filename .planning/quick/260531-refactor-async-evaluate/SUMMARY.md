---
slug: refactor-async-evaluate
date: "2026-05-31"
status: complete
---

# Summary

Refactored `async_evaluate` in `coordinator.py` from a 170-line monolith into
a ~50-line orchestrator backed by three focused private helpers:

- `_compute_desired_temps` — PASS 1 baseline temperature resolution per room
- `_apply_presence_overrides` — PASS 2 presence overrides (mutates in place)
- `_push_temperatures` — async push gather

153 tests pass. No behavior change.

Commit: `a564153`
