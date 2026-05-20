---
quick_id: 260520-q5m
slug: room-person-chip-associations
date: 2026-05-20
status: complete
commits:
  - b304370
files_modified:
  - frontend/src/components/person-card.ts
  - frontend/src/components/room-card.ts
  - custom_components/climate_manager/www/panel.js
---
# Quick Task 260520-q5m: Room/Person Chip Associations — Summary

**person-card.ts**: Replaced ha-checkbox room list with chip UI ([mdi:home-outline] Room Name [×]).
Added "Add room" button that reveals an inline <select> of unassigned rooms on click.
Added @state() _showRoomAdd, _onRoomToggle(), _onAddRoomSelect() methods.
Added panel.reloadConfig() after saves so chips refresh immediately.

**room-card.ts**: Added missing "Associated persons" section with chip UI ([mdi:account] Person Name [×]).
Reads assigned persons from panelConfig.persons (persons whose room_ids includes this roomId).
Modification (add/remove) writes via ws.setPersonConfig() on the targeted person.
Added @state() _showPersonAdd, _getAssignedPersonIds(), _getAllPersonIds(), _getPersonName(),
_onAddPerson(), _onRemovePerson(), _onAddPersonSelect() methods. 
Both sides call panel.reloadConfig() after saves. Build succeeded (99.69 kB), deployed.
