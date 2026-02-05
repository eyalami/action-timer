import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Timer Sensor platform."""
    # Retrieve the manager we stored in __init__.py
    manager = hass.data[DOMAIN][entry.entry_id]
    
    # Hand the 'add' callback to the manager so it can create sensors on the fly
    manager.set_add_entities_callback(async_add_entities)

    # If there were timers restored from storage during manager init, 
    # they are already waiting in manager._timers. 
    # We add them to the UI now.
    if manager._timers:
        _LOGGER.debug("Adding %s restored timers to UI", len(manager._timers))
        async_add_entities(list(manager._timers.values()))