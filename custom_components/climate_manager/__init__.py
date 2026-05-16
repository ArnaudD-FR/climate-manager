"""Climate Manager — Home Assistant custom integration.

Manages home climate controls through smart radiator thermostats.
Provides global heating modes, weekday-based time programs,
per-room schedule overrides, and person presence tracking.

This module is the integration entry point. Platform wiring
(async_setup_entry / async_unload_entry) is added in plan 03.
"""

# Entity platforms managed by this integration.
# Empty in Phase 1 — platforms are wired in plan 03.
PLATFORMS: list[str] = []
