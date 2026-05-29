# Description

This home assistant integration manages the house climate controls.

## Definitions

The system is defined by:

- Global mode:
  - Off: this is a frost protection mode, everything is off unless internal
    temperature goes below minimum defined.
  - Time program: rooms are warmed up depending on time program defined.
  - Time program & presences: rooms are warmed up depending on time program
    defined and on persons presences.

- Period modes:
  - Frost protection, default: 7°C,
  - Reduced, default: 18°C,
  - Normal, default: 20°C,
  - Comfort, default: 22°C,

- Time program: sequence of time periods for week days. A time period stops
  when the next one starts. The last time period of the day stops at midnight.
  Time program is defined by:
  - Weekdays: set of week days (e.g. Monday to Friday, or Saturday and Sunday).
  - Time periods, each time period is defined by:
    - Start time: the time when the period starts.
    - Mode: see period modes.

- Specific periods: those periods sets the system in a specific mode,
  regardless of the global mode.
  - Period types:
    - Holidays at home: the system is set in normal mode from the first time period of the day.
    - Holidays: the system is set in frost protection mode, and warmed up to
      reduced temperature before the end of the period.
  - Start date/time is mandatory. Default start time is midnight.
  - The end date/time is optional. Default end time is 23:59 when enabled.
  - Once end date/time is reached, the system returns to the defined global
    mode and the period is disabled.

- HA rooms: Configurable rooms have at least one smart radiator thermostat
  climate entity associated. Other rooms are ignored by the system. HA rooms are
  defined by:
  - Time program: the time program to apply to the room. If not defined, the
    global time program is applied.

- HA persons:
  - mode:
    - Automatic, the user presence is based on one of the following:
      - Periodic program, sequence of time periods for week days:
        - Weekdays: set of week days (e.g. Monday to Friday, or Saturday and
          Sunday).
        - Time periods, each time period is defined by:
          - Start time: the time when the period starts.
          - Present/absent: the person is present or absent during the period.
      - Calendar: HA calendar entity (at least ical or pronote)
      - GPS tracking
    - Present: the person always in house. Can be used to adjust the system for
      exceptional situations such as a child not attending school, someone
      working remotely.
    - Absent: the person is not in house
  - Rooms: set of rooms associated to the person. If the person is present,
    those rooms are warmed up.

## User interface

The user interface is based on a HA panel. It is split in different sections:

- The global settings section allows to set the global mode, the time program
  and the default temperatures for the different period modes.
- The rooms section allows to set the time program for each room.
- The persons section allows to set the presence mode for each person and the rooms.

## Use cases

### Use case 1: Time program & presence mode

The system is in time program & presence mode.

The rooms are warmed up when the person is present from the first time period
of the day defined as normal or comfort mode until the end of the last time
period of the day defined as normal or comfort mode.

When the person is present and a time period is defined as reduced or frost
protection mode between two normal or comfort mode periods, the room is warmed
up to temperature of the previous time period.

The rooms are not warmed up when the person is absent, the reduced mode is
applied.
