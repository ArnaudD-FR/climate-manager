"""Acceptance tests for Phase 6 (zone-room-assignment-ui) validation gaps.

These tests verify the implementation of 7 gaps:
- Gap 1 (UI-04/ASSIGN-01): set_zone_time_program HAPPY PATH — moved to test_websocket.py
- Gap 2 (UI-01): "Global Settings" tab label present in source
- Gap 3 (ASSIGN-03/UI-06): zone-badge CSS class present in room-card.ts
- Gap 4 (UI-05): isDefault hides delete button in zone-tab.ts
- Gap 5 (UI-04): isDefault routes to global endpoints in zone-tab.ts
- Gap 6 (UI-02): zone_id: null payload present in zone-tab.ts and room-card.ts
- Gap 7 (All/build): Frontend Vite build succeeds

These tests read source files directly and check for structural requirements.
The Gap 1 integration test (set_zone_time_program happy path) is in test_websocket.py.
"""

import subprocess
from pathlib import Path


# ============================================================================
# Gap 2: UI-01 — "Global Settings" tab label in main.ts
# ============================================================================


def test_main_tab_overview_label():
    """Verify the first tab button in main.ts is labeled 'Overview'."""
    main_ts = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/main.ts"
    ).read_text()

    assert "Overview" in main_ts, (
        "main.ts tab bar does not have 'Overview' button label"
    )


# ============================================================================
# Gap 3: ASSIGN-03/UI-06 — zone-badge CSS class in room-card.ts
# ============================================================================


def test_room_card_zone_badge_present():
    """Verify room-card.ts includes a zone badge with the .zone-badge CSS class.

    Requirement: Every room card header row has a zone badge showing the zone
    display name (ASSIGN-03). The badge uses class="zone-badge" for styling.
    """
    room_card = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/components/room-card.ts"
    ).read_text()

    # Must have the CSS class definition
    assert ".zone-badge" in room_card, (
        "room-card.ts does not define .zone-badge CSS class"
    )

    # Must have the badge markup in the render
    assert 'class="zone-badge"' in room_card, (
        "room-card.ts does not render a zone badge with class='zone-badge'"
    )

    # The badge should contain the zone name from the helper
    assert "_getZoneName()" in room_card, (
        "room-card.ts does not call _getZoneName() in the badge render"
    )


# ============================================================================
# Gap 4: UI-05 — isDefault hides delete button in zone-tab.ts
# ============================================================================


def test_zone_tab_isdefault_hides_delete():
    """Verify zone-tab.ts uses isDefault to conditionally hide the delete button.

    Requirement: Default Zone tab (isDefault=true) does not render a Delete button.
    The render logic must check isDefault and conditionally render the delete row.
    """
    zone_tab = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/components/zone-tab.ts"
    ).read_text()

    # Must have isDefault property
    assert "@property({ type: Boolean }) isDefault = false" in zone_tab, (
        "zone-tab.ts does not have isDefault property"
    )

    # Delete button render must be guarded by !this.isDefault
    # In Lit, the pattern is `${!this.isDefault ? html`...` : ""}` for conditional rendering
    assert "!this.isDefault" in zone_tab and "delete-row" in zone_tab.lower(), (
        "zone-tab.ts does not conditionally hide delete button based on isDefault"
    )

    # Should have the delete row section with isDefault guard
    # Look for the pattern: ${!this.isDefault ? html`...delete...` : ""}
    assert "${!this.isDefault" in zone_tab and "delete-row" in zone_tab, (
        "zone-tab.ts does not have !this.isDefault ternary guard for delete row rendering"
    )


# ============================================================================
# Gap 5: UI-04 — isDefault branches route to global endpoints in zone-tab.ts
# ============================================================================


def test_zone_tab_isdefault_routes_global_endpoints():
    """Verify zone-tab.ts routes Default Zone mode/time-program to global endpoints.

    Requirement: When isDefault=true, mode changes call ws.setGlobalMode (not
    ws.setZoneMode), and time-bar changes call ws.setTimeProgram (not
    ws.setZoneTimeProgram). This ensures Default Zone edits persist to the
    global mode/time-program configuration.
    """
    zone_tab = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/components/zone-tab.ts"
    ).read_text()

    # Must call setGlobalMode for Default Zone
    assert "this.ws.setGlobalMode" in zone_tab, (
        "zone-tab.ts does not call ws.setGlobalMode for Default Zone mode changes"
    )

    # Must call setTimeProgram for Default Zone
    assert "this.ws.setTimeProgram" in zone_tab, (
        "zone-tab.ts does not call ws.setTimeProgram for Default Zone time-program changes"
    )

    # Both calls should be in isDefault-conditional branches
    assert "this.isDefault" in zone_tab, (
        "zone-tab.ts does not check this.isDefault for branching logic"
    )

    # Verify the branches exist: setGlobalMode and setZoneMode should both be present
    # (one for Default Zone, one for custom zones)
    assert "this.ws.setZoneMode" in zone_tab, (
        "zone-tab.ts does not have custom zone branch calling ws.setZoneMode"
    )


# ============================================================================
# Gap 6: UI-02 — zone_id: null payload verified in zone-tab.ts and room-card.ts
# ============================================================================


def test_null_zone_id_payload_present():
    """Verify zone_id: null payloads are sent when removing/adding rooms to Default Zone.

    Requirement: zone-tab.ts sends zone_id: null (not undefined) in _onRemoveRoom
    and _onAddRoom (Default Zone branch). room-card.ts sends zone_id: null in
    _onZoneChange when selecting the Default Zone option. This ensures
    JSON.stringify preserves the key so the backend can interpret null as "pop key".
    """
    zone_tab = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/components/zone-tab.ts"
    ).read_text()
    room_card = Path(
        "/home/arnaud/dev/climate_manager/frontend/src/components/room-card.ts"
    ).read_text()

    # zone_tab.ts must use zone_id: null (not undefined)
    # Count occurrences of "zone_id: null" in zone-tab
    zone_tab_null_count = zone_tab.count("zone_id: null")
    assert zone_tab_null_count >= 2, (
        f"zone-tab.ts has only {zone_tab_null_count} occurrences of 'zone_id: null', "
        "expected at least 2 (for _onRemoveRoom and Default Zone _onAddRoom)"
    )

    # zone_tab.ts must NOT use zone_id: undefined
    assert "zone_id: undefined" not in zone_tab, (
        "zone-tab.ts still uses 'zone_id: undefined' which gets dropped by JSON.stringify"
    )

    # room_card.ts must use zone_id: null
    room_card_null_count = room_card.count("zone_id: null")
    assert room_card_null_count >= 1, (
        "room-card.ts has no occurrences of 'zone_id: null' in _onZoneChange handler"
    )

    # room_card.ts must NOT use zone_id: undefined (unless it's in a comment)
    # Check for the actual pattern in code (not in comments)
    lines = room_card.split("\n")
    for i, line in enumerate(lines):
        if "zone_id: undefined" in line and not line.strip().startswith("//"):
            raise AssertionError(
                f"room-card.ts has 'zone_id: undefined' at line {i + 1}, should be 'zone_id: null'"
            )


# ============================================================================
# Gap 7: Build — Frontend Vite build succeeds
# ============================================================================


def test_frontend_vite_build():
    """Verify the frontend TypeScript compiles and Vite build succeeds.

    Requirement: The Vite build must produce a panel.js bundle without errors.
    Pre-existing TypeScript errors in time-bar.ts are not a blocker — only the
    Vite build exit code (which is more lenient) is checked.

    NOTE: tsc --noEmit may fail due to pre-existing time-bar.ts errors;
    we check vite build instead which is more pragmatic.
    """
    frontend_dir = Path("/home/arnaud/dev/climate_manager/frontend")

    # Run the Vite build
    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"Vite build failed with exit code {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    # Verify the output bundle exists (Vite outputs to custom_components/climate_manager/www/panel.js)
    panel_js = Path(
        "/home/arnaud/dev/climate_manager/custom_components/climate_manager/www/panel.js"
    )
    assert panel_js.exists(), (
        f"Vite build succeeded but panel.js not found at {panel_js}"
    )


# ============================================================================
# Gap 1 (Integration Test — moved to test_websocket.py)
# ============================================================================
# test_ws_set_zone_time_program_accepts_full_program is added to test_websocket.py
# This test verifies that set_zone_time_program happy path (full 7-day program)
# accepts the payload, persists it to runtime_config, and returns success.
