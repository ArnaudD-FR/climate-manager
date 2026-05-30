---
quick_id: 260529-b3c
slug: overview-per-zone-status
status: complete
date: 2026-05-29
commit: db5a5c1
---

# Quick Task 260529-b3c: Overview per-zone status

**Overview tab Current Status card now shows per-zone breakdown instead of single global mode row**

- global-settings-tab.ts: added `getActivePeriod(program, now)` exported helper — evaluates the active schedule period from a DailyProgram at the given time (Mon=0..Sun=6 remap, finds last period starting ≤ now)
- global-settings-tab.ts: added `_getZoneRows()` method — builds rows for Default Zone (mode+period from backend status) + each custom zone (mode from config, period computed client-side)
- global-settings-tab.ts: replaced flat Mode + Active period `.status-row` entries with `.zone-status-grid` table (Zone / Mode / Active period columns); zone names are clickable → `panel.navigateToZone()`
- global-settings-tab.ts: added CSS for `.zone-status-grid`, `.zone-status-header`, `.zone-status-row`, `.zone-status-name`, `.zone-status-value`
- types.ts import: added `getZoneColor` for zone name color coding
