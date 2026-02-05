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
    
    # שמירת המנהל ב-hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    # הגדרת פלטפורמת הסנסור
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def async_set_timer(call: ServiceCall):
        """Service to create a new timer."""
        target_entity = call.data.get("entity_id")
        duration = call.data.get("duration")
        service = call.data.get("service_to_call", "homeassistant.turn_off")
        
        # איסוף כל שאר השדות (כמו message, title) כפרמטרים לפעולה
        action_params = {
            k: v for k, v in call.data.items() 
            if k not in ["duration", "service_to_call"]
        }

        action_config = {
            "action": service,
            "data": action_params
        }
        
        # יצירת הטיימר - ה-Manager יחולל UUID פנימי
        await manager.create_timer_entity(target_entity, duration, action_config)

    async def async_cancel_timer(call: ServiceCall):
        """Service to cancel an existing timer by its sensor entity_id."""
        # כאן אנחנו מצפים לקבל את ה-ID של הסנסור (למשל sensor.at_a1b2c3d4)
        timer_entity_id = call.data.get("timer_entity_id")
        
        if not timer_entity_id:
            _LOGGER.warning("Cancel timer called without timer_entity_id")
            return

        # חילוץ ה-timer_id (הסרת הקידומת 'sensor.')
        timer_id = timer_entity_id.split(".")[-1]

        if timer_id in manager._timers:
            await manager.remove_timer(timer_id)
            _LOGGER.info("ActionTimer %s was cancelled manually", timer_id)
        else:
            _LOGGER.warning("Timer ID %s not found in active timers", timer_id)

    # רישום השירותים
    hass.services.async_register(DOMAIN, SERVICE_SET_TIMER, async_set_timer)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_TIMER, async_cancel_timer)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id)
        # ניקוי כל הטיימרים הפעילים בעת הסרת האינטגרציה
        for tid in list(manager._timers.keys()):
            await manager.remove_timer(tid)
            
    return unload_ok