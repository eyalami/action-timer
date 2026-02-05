import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from .const import DOMAIN, SERVICE_SET_TIMER, SERVICE_CANCEL_TIMER
from .manager import TimerManager

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the component from a Config Entry."""
    manager = TimerManager(hass)
    await manager.async_added_to_hass()
    
    # Store manager in hass.data so sensor.py can access it
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    # Set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def async_set_timer(call: ServiceCall):
        """Service to create a new timer."""
        entity_id = call.data.get("entity_id")
        duration = call.data.get("duration")
        service_to_call = call.data.get("service_to_call", "homeassistant.turn_off")
        
        # Capture all extra data for the target service call
        service_data = dict(call.data)
        service_data.pop("duration", None)
        service_data.pop("service_to_call", None)

        action_config = {"action": service_to_call, "data": service_data}
        await manager.create_timer_entity(entity_id, duration, action_config)

    async def async_cancel_timer(call: ServiceCall):
        """Service to cancel an existing timer by its entity_id."""
        entity_id = call.data.get("entity_id")
        for tid, entity in list(manager._timers.items()):
            if entity._timer_data.entity_id == entity_id:
                await manager.remove_timer(tid)
                _LOGGER.info("Timer for %s was cancelled manually", entity_id)

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_TIMER, async_set_timer)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_TIMER, async_cancel_timer)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id)
        # Clean up all active timers on unload
        for tid in list(manager._timers.keys()):
            await manager.remove_timer(tid)
            
    return unload_ok