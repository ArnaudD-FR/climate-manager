---
quick_id: 260603-uo0
status: complete
date: 2026-06-03
---

# Summary: Matter→Tado X Drag-and-Drop Pairing UI

## What was done

### room-card.ts
- Rewrote `_renderClimateSection()` — removed the old select/chip UI,
  replaced with a two-level vertical tree
- Added `@state() _dragActive` and `_dragType` for drag lifecycle tracking
- Added `_entityName(id)` helper (reads `friendly_name` from hass.states)
- Full HTML5 DnD handler set: `_startDrag`, `_onDragEnd`,
  `_onMatterDragOver`, `_onAnyDragOver`, `_onMatterDragEnter`,
  `_onMatterDragLeave`, `_parseDragPayload`, `_onDropOnTado`,
  `_onDropOnUnassign`
- `canPair` gate: drag features enabled only when room has ≥1 Tado X
  entity AND ≥1 Matter entity
- L1 renders Tado X groups and independent entities sorted by friendly name
- L2 renders Matter children under each group, sorted by friendly name
- Unassign drop zone appears on the right only while a drag is active
- All chips use `mdi:thermometer`; draggable chips carry `.chip-draggable`
- Drag ghost follows cursor via `setDragImage`; text selection suppressed
- `dragenter`/`dragleave` flicker fixed via `relatedTarget.contains()`

### shared-styles.ts
- New `groupDndStyles` export with all DnD layout CSS:
  `.climate-pair`, `.climate-tree`, `.tado-group`, `.matter-children`,
  `.chip-draggable`, `.chip-temp`, `.chip.drag-over`,
  `.unassign-drop-zone`

### __init__.py
- Added `import json`
- `async_setup_entry` reads `manifest.json` version and appends
  `?v=<version>` to the panel `module_url`, busting the browser cache on
  every new release

## Outcome

The Matter→Tado X pairing section in each room card now uses drag-and-drop
instead of selects. Entities display as a two-level vertical tree. Browser
cache is invalidated automatically on each deploy via the version suffix.
