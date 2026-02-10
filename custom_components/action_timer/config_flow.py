from typing import Any
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from .const import DOMAIN

class ActionTimerConfigFlow(ConfigFlow, domain=DOMAIN):  
    """Handle a config flow for Action Timer."""
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Ensure only one instance of the integration is configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Action Timer", data={})

        return self.async_show_form(step_id="user")