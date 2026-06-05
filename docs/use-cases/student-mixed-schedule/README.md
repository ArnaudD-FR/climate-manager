# Lena — Student Mixed Schedule

Lena is a student whose class hours change from day to day: Monday has multiple
blocks with gaps, Tuesday runs a long morning block, Wednesday is completely
free, and Thursday and Friday each have their own pattern. This example shows
how a **scheduled (single week)** presence schedule can express varied
per-weekday timetables, not just a repeating pattern.

## Configuration Summary

The table below is the Configuration Summary for this use case.

| Property       | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| Presence mode  | `scheduled` (single week)                                          |
| Schedule shape | Varies per weekday — different class hours each day, home weekends |
| Assigned rooms | Bedroom                                                            |

## Screenshots

### Persons tab — Lena card expanded

![Lena person card expanded](screenshots/persons.png)

The expanded card highlights the per-day time bars: each weekday shows a
different block pattern reflecting Lena's varying class timetable, while
Saturday and Sunday are fully present.
