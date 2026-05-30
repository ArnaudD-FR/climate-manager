---
quick_id: 260529-a1b
slug: person-room-cross-navigation
status: complete
date: 2026-05-29
commit: e107d14
---

# Quick Task 260529-a1b: Person/room cross-navigation

**Person chip in room card → Persons tab + expand person card**
- room-card.ts: person chips get `@click → panel.navigateToPerson(personId)`; remove button stops propagation; chip CSS adds cursor:pointer + hover border

**Room chip in person card → Rooms tab + expand room card**
- person-card.ts: room chips get `@click → panel.navigateToRoom(roomId)`; remove button stops propagation; chip CSS adds cursor:pointer + hover border
- person-card.ts: added `autoExpand` prop + `updated()` expand/scroll handler (same pattern as room-card)
- main.ts: `navigateToPerson()` + `_expandPersonId` state; passes `expandPersonId` to persons-tab
- persons-tab.ts: receives `expandPersonId`, passes `autoExpand` per card
