import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, SENSOR, SERVICE_SET_TIMER, SERVICE_CANCEL_TIMER
from .manager import ActionTimerManager

_LOGGER = logging.getLogger(__name__)

SET_TIMER_SCHEMA = vol.Schema({
    vol.Required("duration"): vol.All(cv.positive_int, vol.Range(min=1)),
    vol.Required("run_at_end"): cv.ensure_list,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    #init the manager
    manager = ActionTimerManager(hass)
    
    # perform async setup tasks (like restoring timers from storage)
    await manager.load_and_sync()
    
    # store the manager in hass.data so sensor.py can access it
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    async def async_set_timer(call: ServiceCall):
        """Service to create a new timer."""
        duration = call.data.get("duration", 60)
        action_config = call.data.get("action_config", [])
        
        await manager.create_timer(duration, action_config)


    async def async_cancel_timer(call: ServiceCall):
        """Service to cancel an existing timer by its sensor entity_id."""
        timer_entity_id = call.data.get("action_timer_id")
        
        if not timer_entity_id:
            _LOGGER.warning("Cancel timer called without timer_entity_id")
            return
        
        # Extract the unique timer ID from the entity_id (e.g., sensor.at_a1b2c3d4 -> at_a1b2c3d4)
        timer_id = timer_entity_id.split(".")[-1]

        if timer_id in manager.timers:
            await manager.remove_timer(timer_id)
            _LOGGER.info("ActionTimer %s was cancelled manually", timer_id)
        else:
            _LOGGER.warning("Timer ID %s not found in active timers", timer_id)

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_TIMER, async_set_timer, schema=SET_TIMER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_TIMER, async_cancel_timer)
    
    # Forward the config entry to the sensor platform, which will set up the entities
    await hass.config_entries.async_forward_entry_setups(entry, [SENSOR])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [SENSOR])
    
    if unload_ok:
        manager: ActionTimerManager = hass.data[DOMAIN].pop(entry.entry_id)
        # clear all timers when unloading
        await manager.remove_all_timers()
            
    return unload_ok