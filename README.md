# Climate Manager

A Home Assistant custom integration that manages home climate controls through
smart radiator thermostats (TRVs). It provides zone-based heating modes, weekday
time programs, per-room schedule overrides, and person presence tracking — all
configurable through a full Lovelace dashboard panel.

> **Core value:** Every room is always at the right temperature at the right
> time, without manual intervention — driven by schedules and who is actually
> home.

---

## Screenshots

### Overview tab

![Overview tab](docs/screenshots/overview.png)

### Rooms tab

![Rooms tab](docs/screenshots/rooms.png)

### Zone tab (Home — default zone)

![Zone tab](docs/screenshots/zone.png)

### Zone tab (Upstairs — Time program & presences)

![Zone Upstairs tab](docs/screenshots/zone-upstairs.png)

### Persons tab

![Persons tab](docs/screenshots/persons.png)

### Global Settings tab

![Global Settings tab](docs/screenshots/global-settings.png)

---

## Features

- **Zone-based scheduling** — Group rooms into zones, each with its own weekly
  heating program (Normal, Comfort, Reduced, Frost Protection periods)
- **Three heating modes per zone** — _Off_, _Time program_, _Time program &
  presences_
- **Per-room overrides** — Each room can follow its zone program, use a custom
  schedule, or be set to Off individually
- **Person presence** — Associate persons with rooms; in _Time program &
  presences_ mode the room only heats when someone is home
- **Presence tracking modes** — Scheduled (weekly timetable), HA home tracking,
  Force Present, Force Absent
- **Gap-fill logic** — When a person is present, Reduced/Frost periods
  sandwiched between Normal/Comfort periods are held at the preceding
  Normal/Comfort temperature
- **Live status** — Overview tab shows current period, temperature, and humidity
  for every room
- **TRV control** — Works with any HA `climate` entity; no brand-specific APIs

---

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/your-repo/climate_manager` as an Integration
3. Search for **Climate Manager** and install
4. Restart Home Assistant
5. Go to Settings → Integrations → Add Integration → **Climate Manager**

### Manual

1. Copy `custom_components/climate_manager/` into your HA
   `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Integrations → Add Integration → **Climate Manager**

---

## How it works

### Zones and modes

Rooms are grouped into **zones**. Each zone has a **mode**:

| Mode                         | Behaviour                                                         |
| ---------------------------- | ----------------------------------------------------------------- |
| **Off**                      | All rooms in the zone are kept at frost protection temperature    |
| **Time program**             | Rooms follow the zone's weekly schedule                           |
| **Time program & presences** | Rooms follow the schedule only when an assigned person is present |

### Time program

A weekly schedule divided into days (Mon–Sun). Each day has periods with a start
time and a mode:

| Period               | Typical use                                           |
| -------------------- | ----------------------------------------------------- |
| **Normal**           | Standard daytime temperature                          |
| **Comfort**          | Higher temperature (e.g. weekends, working from home) |
| **Reduced**          | Lower temperature (sleeping, away)                    |
| **Frost Protection** | Minimum anti-freeze temperature                       |

Each period is active from its start time until the next period's start. The
last period of the day runs until midnight.

### Presence & scheduling

When a zone is in _Time program & presences_ mode:

- **Person absent** → room stays at Reduced temperature regardless of the
  schedule
- **Person present** → room is heated from the first Normal/Comfort period to
  the last
- **Gap-fill** — A Reduced or Frost period sandwiched between two Normal/Comfort
  periods is held at the preceding Normal/Comfort temperature while someone is
  present

**Example:** schedule Normal 06:00 → Reduced 09:00 → Normal 17:00 → Frost 22:00.
If present all day: room heats 06:00–22:00, holding Normal during the
09:00–17:00 Reduced gap. If absent: room stays at Reduced all day.

### Per-room overrides

Each room has a **mode** that can override its zone:

| Room mode          | Behaviour                                     |
| ------------------ | --------------------------------------------- |
| **Zone program**   | Follows the zone's schedule and mode          |
| **Custom program** | Uses its own schedule; zone Off still applies |
| **Off**            | Frost protection only, regardless of zone     |

---

## Configuration

All configuration is done through the panel UI accessible from the HA sidebar.
No YAML editing required.

### Global settings

- Period temperatures (Normal, Comfort, Reduced, Frost Protection)
- Default zone name

### Zones

- Create and name zones
- Set zone mode (Off / Time program / Time program & presences)
- Edit the weekly time program
- Assign rooms to zones

### Rooms

- Set per-room mode (Zone program / Custom program / Off)
- Edit custom schedule (when in Custom mode)
- Assign persons to a room
- Assign room to a zone

### Persons

- Set presence mode (Scheduled / HA home tracking / Force Present / Force
  Absent)
- Edit presence schedule
- Assign rooms

---

## Requirements

- Home Assistant 2025.x or later
- Smart thermostat(s) exposed as HA `climate` entities
- Python 3.12+

---

## Development

```bash
# Install dependencies
uv sync

# Run tests
make test

# Build frontend
make build

# Deploy to HA instance (requires SSH access)
make deploy

# Regenerate README screenshots (requires Docker)
make screenshots
```

Frontend stack: Lit 3.x · TypeScript 5.x · Vite 5.x

---

## License

[MIT](LICENSE)
