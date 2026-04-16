from __future__ import annotations

from homeassistant import config_entries
from .const import DOMAIN


class MeaElectricityTariffsFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MEA Electricity Tariffs."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title="MEA Electricity Tariffs", data={})
