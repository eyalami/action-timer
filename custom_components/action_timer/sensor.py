import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR
from .manager import ActionTimerManager
from .models import ActionTimerData


_LOGGER = logging.getLogger(__name__)


class ActionTimerSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_should_poll = False
    _attr_has_entity_name = True
    
    def __init__(self, timer_data: ActionTimerData):
        """Initialize the timer entity."""
        timer_id = timer_data.id
        self._timer_data = timer_data
        
        self._attr_unique_id = timer_id
        self.entity_id = f"{SENSOR}.{timer_id}"
        self._attr_name = f"Action Timer: {timer_id}"  # Shorten for display
      
        self._attr_native_value = timer_data.expiration
        self._attr_extra_state_attributes = {
            "duration": timer_data.duration,
            "created_at": timer_data.created_at.isoformat(),
            "expiration": timer_data.expiration.isoformat(),
            "action_config": timer_data.action_config
        }

    async def async_added_to_hass(self):
        """Called when the entity is added to Home Assistant."""
        
        @callback
        def _async_on_timer_finished(event: Event):
            """Internal callback to handle the termination signal."""
            if event.data.get("timer_id") == self._timer_data.id:
                self.hass.async_create_task(self.async_remove())

        # Register the listener and ensure it is cleaned up automatically
        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_timer_finished", _async_on_timer_finished)
        )


async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Timer Sensor platform."""
    # Retrieve the manager we stored in __init__.py
    manager: ActionTimerManager = hass.data[DOMAIN][entry.entry_id]
    
    # hand the 'add' callback to the manager so it can create sensors 
    manager.setup_entity_platform(async_add_entities)

