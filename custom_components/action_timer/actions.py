import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant, Context
from homeassistant.helpers import service, script
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_execute_action(
    hass: HomeAssistant,
    action_config: ConfigType,
    context: Context,
    variables: Dict[str, Any] = None
) -> bool:
    """Execute a configured action."""
    if not action_config:
        return False

    action_type = next(iter(action_config))
    action_data = action_config[action_type]

    try:
        if action_type == "service":
            return await service.async_call_from_config(
                hass,
                action_data,
                blocking=True,
                context=context,
                variables=variables
            )
        elif action_type == "script":
            return await script.async_call_from_config(
                hass,
                action_data,
                blocking=True,
                context=context,
                variables=variables
            )
        elif action_type == "event":
            hass.bus.async_fire(
                action_data["event_type"],
                action_data.get("event_data", {}),
                context=context
            )
            return True
        elif action_type == "delay":
            await script.async_delay(
                hass,
                action_data["delay"],
                action_data.get("name", "Timer Component Delay")
            )
            return True
    except Exception as e:
        _LOGGER.error("Error executing action %s: %s", action_type, str(e))
        return False

    _LOGGER.error("Unknown action type: %s", action_type)
    return False