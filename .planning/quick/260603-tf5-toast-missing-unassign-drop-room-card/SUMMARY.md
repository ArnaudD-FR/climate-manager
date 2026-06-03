---
slug: tf5-toast-missing-unassign-drop-room-card
status: complete
date: 2026-06-03
commit: 2b9b30f
---

## Summary

Added `showToast` feedback to `_onDropOnUnassign` in `room-card.ts`.

Both unassign paths (Tado X full-clear and Matter entity removal from a mapping)
were silently succeeding or failing with no user feedback. The fix wraps both
paths in a single try/catch and calls `showToast("Saved", false)` on success
and `showToast("Save failed — retrying...", true)` on error — consistent with
every other save handler in the file.

## Files changed

- `frontend/src/components/room-card.ts` — `_onDropOnUnassign` (line 777)
