---
slug: tf5-toast-missing-unassign-drop-room-card
title: Fix toast missing on unassign drop in room-card.ts
date: 2026-06-03
status: in-progress
---

## Goal

Add `showToast` calls to `_onDropOnUnassign` in `room-card.ts` so the user gets
feedback after a successful unassign drag-and-drop, consistent with every other
save operation in the file.

## Root Cause

`_onDropOnUnassign` (line 777) has two success paths:
1. `d.type === "tadox"` — clears the full mapping for a Tado X entity
2. Matter entity — removes a single Matter entity from a Tado X mapping

Neither path calls `this.panel.showToast(...)`. Every other save handler in
the file wraps the WS call in try/catch and shows "Saved" or "Save failed".

## Fix

File: `frontend/src/components/room-card.ts`

Wrap both save paths in `_onDropOnUnassign` with try/catch and add:
- `this.panel.showToast("Saved", false)` on success
- `this.panel.showToast("Save failed — retrying...", true)` on error

## Tasks

- [ ] Edit `_onDropOnUnassign` in `room-card.ts`
- [ ] Run `make lint` to validate
- [ ] Run `make build` to confirm no compile errors
- [ ] Commit
