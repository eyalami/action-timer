import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_SET_TIMER, SERVICE_CANCEL_TIMER
from .manager import TimerManager
from .store import TimerStore

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the timer component."""
    # Initialize storage
    store = TimerStore(hass)
    
    # Initialize manager
    manager = TimerManager(hass)
    
    # Load existing timers
    await manager.async_added_to_hass()
    
    # Register services
    async def async_register_services():
        async def async_set_timer(call):
            """Set a new timer."""
            entity_id = call.data.get("entity_id")
            duration = call.data.get("duration")
            service_to_call = call.data.get("service_to_call", SERVICE_TURN_OFF)
            
            if not entity_id or not duration:
                _LOGGER.error("Missing required parameters for set_timer")
                return
                
            await manager.create_timer_entity(entity_id, duration, service_to_call)
            
        async def async_cancel_timer(call):
            """Cancel an existing timer."""
            entity_id = call.data.get("entity_id")
            
            if not entity_id:
                _LOGGER.error("Missing required parameter for cancel_timer")
                return
                
            # Find and remove timer
            for timer_id, timer_entity in manager._timers.items():
                if timer_entity.entity_id == entity_id:
                    await manager.remove_timer(timer_id)
                    break
                    
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TIMER,
            async_set_timer,
            description="Create a new timer that will call a service after specified duration"
        )
        
        hass.services.async_register(
            DOMAIN,
            SERVICE_CANCEL_TIMER,
            async_cancel_timer,
            description="Cancel an existing timer"
        )
        
    await async_register_services()
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the timer component entry."""
    # Initialize storage
    store = TimerStore(hass)
    
    # Initialize manager
    manager = TimerManager(hass)
    
    # Load existing timers
    await manager.async_added_to_hass()
    
    # Register services
    async def async_register_services():
        async def async_set_timer(call):
            """Set a new timer."""
            entity_id = call.data.get("entity_id")
            duration = call.data.get("duration")
            service_to_call = call.data.get("service_to_call", SERVICE_TURN_OFF)
            
            if not entity_id or not duration:
                _LOGGER.error("Missing required parameters for set_timer")
                return
                
            await manager.create_timer_entity(entity_id, duration, service_to_call)
            
        async def async_cancel_timer(call):
            """Cancel an existing timer."""
            entity_id = call.data.get("entity_id")
            
            if not entity_id:
                _LOGGER.error("Missing required parameter for cancel_timer")
                return
                
            # Find and remove timer
            for timer_id, timer_entity in manager._timers.items():
                if timer_entity.entity_id == entity_id:
                    await manager.remove_timer(timer_id)
                    break
                    
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TIMER,
            async_set_timer,
            description="Create a new timer that will call a service after specified duration"
        )
        
        hass.services.async_register(
            DOMAIN,
            SERVICE_CANCEL_TIMER,
            async_cancel_timer,
            description="Cancel an existing timer"
        )
        
    await async_register_services()
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the timer component."""
    # Remove all timers
    for timer_id in list(manager._timers.keys()):
        await manager.remove_timer(timer_id)
        
    return True