---
quick_id: 260528-9r2
slug: zone-room-cross-navigation
status: complete
date: 2026-05-28
commit: 11df36b
---

# Quick Task 260528-9r2: Zone/room cross-navigation

Two linked navigation features implemented:

**Zone badge → zone tab (room-card.ts)**
- Added `cursor: pointer` + `:hover { opacity: 0.8 }` to `.zone-badge`
- Click handler calls `panel.navigateToZone(config?.zone_id)` with `e.stopPropagation()` to avoid toggling the card expand

**Room chip → rooms tab + expand (zone-tab.ts + rooms-tab.ts + room-card.ts + main.ts)**
- Zone-tab chips now `cursor: pointer` with hover border highlight
- Chip click calls `panel.navigateToRoom(roomId)`; remove button stops propagation
- `main.ts`: added `navigateToZone()` + `async navigateToRoom()` public methods; `_expandRoomId` state cleared after one render cycle
- `rooms-tab.ts`: receives `expandRoomId`, passes `autoExpand` boolean per card
- `room-card.ts`: `autoExpand` prop triggers `_expanded = true` + `scrollIntoView` in `updated()`
