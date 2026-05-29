"""Climate Manager config flow.

Provides ClimateManagerFlowHandler: a single-step config flow that creates
the integration entry immediately when the user clicks Submit.

Design decisions (from RESEARCH.md):
- Pattern 1: Minimal single-instance config flow
- D-04: Single step, no user fields — all real config is in the panel (Phase 3)
- D-05: Single-instance enforcement via single_config_entry: true in manifest
  (Pitfall 5 — manifest gate is cleaner than flow-level abort)
- T-01-09: No user input accepted — no validation needed, no injection surface
"""

from homeassistant import config_entries

from .const import DOMAIN


class ClimateManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Climate Manager config flow.

    Single step: user clicks Submit → entry created with empty data.
    Single-instance enforcement is handled by single_config_entry: true in
    manifest.json (HA blocks the flow before it starts on second install).
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step.

        If the user submitted the form (user_input is not None), create the
        config entry immediately with empty data (D-04 — no user fields).
        Otherwise, show the empty form with a single Submit button.
        """
        if user_input is not None:
            return self.async_create_entry(
                title="Climate Manager",
                data={},
            )
        return self.async_show_form(step_id="user")
