import logging
from datetime import timedelta
from typing import Dict, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_point_in_time
# USE dt_util for timezone awareness
from homeassistant.util import slugify, dt as dt_util

from .const import DOMAIN
from .models import TimerData

_LOGGER = logging.getLogger(__name__)
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1

class TimerEntity(Entity):
    """Representation of an ActionTimer entity for the UI."""
    _attr_device_class = "timestamp"

    def __init__(self, timer_id: str, timer_data: TimerData, manager):
        """Initialize the timer entity."""
        self._timer_id = timer_id
        self._timer_data = timer_data
        self._manager = manager
        # Initialize the handle for the background task
        self._unsub_expiration = None

        # Set the entity ID clearly
        self.entity_id = f"sensor.{slugify(timer_data.entity_id)}_action_timer"

    @property
    def name(self) -> str:
        """Return the friendly name."""
        return f"ActionTimer: {self._timer_data.entity_id}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID based on creation time."""
        return f"{self._timer_data.entity_id}_{self._timer_data.created_at.timestamp()}"

    @property
    def state(self) -> str:
        """Return the expiration time as the state for the UI countdown."""
        return self._timer_data.expiration.isoformat()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Attributes for both UI cards and tracking."""
        return {
            "duration": self._timer_data.duration,
            "start_time": self._timer_data.created_at.isoformat(),
            "target_entity": self._timer_data.entity_id,
            "action_config": self._timer_data.action_config,
            "expiration": self._timer_data.expiration.isoformat(),
            "created_at": self._timer_data.created_at.isoformat()
        }

class TimerManager:
    """Manage ActionTimer entities and storage."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._timers: Dict[str, TimerEntity] = {}
        self._data: Dict[str, TimerData] = {}
        self._async_add_entities = None

    def set_add_entities_callback(self, async_add_entities):
        self._async_add_entities = async_add_entities

    async def async_added_to_hass(self):
        await self._load_timers()
        await self.grace_period_check()

    async def _load_timers(self):
        if (data := await self._store.async_load()) is not None:
            for timer_id, timer_data in data.items():
                self._data[timer_id] = TimerData.from_dict(timer_data)

    async def _save_timers(self):
        data = {tid: tdata.to_dict() for tid, tdata in self._data.items()}
        await self._store.async_save(data)

    async def create_timer_entity(self, target_entity: str, duration: int, action_config: Dict[str, Any]) -> TimerEntity:
        """Create and register a new timer entity."""
        # Use dt_util.now() for HA compatibility
        now = dt_util.now()
        timer_id = f"{slugify(target_entity)}_{now.timestamp()}"
        expiration = now + timedelta(seconds=duration)
        
        timer_data = TimerData(
            entity_id=target_entity,
            duration=duration,
            action_config=action_config,
            expiration=expiration
        )
        
        self._data[timer_id] = timer_data
        timer_entity = TimerEntity(timer_id, timer_data, self)
        self._timers[timer_id] = timer_entity
        
        if self._async_add_entities:
            self._async_add_entities([timer_entity])
        
        # IMPORTANT: Save the return handle to allow cancellation
        timer_entity._unsub_expiration = async_track_point_in_time(
            self.hass, 
            self._async_on_expiration(timer_id), 
            expiration
        )
        
        await self._save_timers()
        _LOGGER.info("ActionTimer created for %s", target_entity)
        return timer_entity

    @callback
    def _async_on_expiration(self, timer_id: str):
        async def _async_expired(now):
            await self._async_execute_and_remove(timer_id)
        return _async_expired

    async def _async_execute_and_remove(self, timer_id: str):
        timer_data = self._data.get(timer_id)
        if not timer_data:
            return

        action = timer_data.action_config.get("action")
        service_data = timer_data.action_config.get("data", {})
        
        try:
            domain, service = action.split(".")
            if domain == "persistent_notification":
                service_data = {k: v for k, v in service_data.items() if k != "entity_id"}

            await self.hass.services.async_call(domain, service, service_data)
        except Exception as err:
            _LOGGER.error("Failed to execute ActionTimer: %s", err)
        
        await self.remove_timer(timer_id)

    async def remove_timer(self, timer_id: str):
        """Cleanly remove the timer and stop background tasks."""
        if timer_entity := self._timers.pop(timer_id, None):
            # 1. Stop the task from firing if it exists
            if timer_entity._unsub_expiration:
                timer_entity._unsub_expiration()
            
            # 2. Remove the entity from HA
            timer_entity.async_remove()
        
        self._data.pop(timer_id, None)
        await self._save_timers()

    async def grace_period_check(self):
        """Cleanup expired timers from previous session."""
        now = dt_util.now()
        expired_timers = [tid for tid, td in self._data.items() if td.expiration <= now]
        for tid in expired_timers:
            await self.remove_timer(tid)