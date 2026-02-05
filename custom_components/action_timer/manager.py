import logging
from datetime import timedelta
from typing import Dict, Any
import uuid

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers import entity_registry as er
# USE dt_util for timezone awareness
from homeassistant.util import dt as dt_util

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

        # Use the UNIQUE timer_id (e.g., at_a1b2c3d4) for the entity_id
        # This allows multiple timers for the same target entity
        self.entity_id = f"sensor.{timer_id}"

    @property
    def name(self) -> str:
        """Friendly name that shows what this timer is doing."""
        return f"Action: {self._timer_data.action_config.get('action')} on {self._timer_data.entity_id}"

    @property
    def unique_id(self) -> str:
        """The internal unique ID."""
        return self._timer_id

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
        """Load timers from storage and re-initialize them."""
        if (data := await self._store.async_load()) is not None:
            new_entities = []
            for timer_id, timer_data_dict in data.items():
                timer_data = TimerData.from_dict(timer_data_dict)
                self._data[timer_id] = timer_data
                
                # check if the timer is still valid
                if timer_data.expiration > dt_util.now():
                    timer_entity = TimerEntity(timer_id, timer_data, self)
                    self._timers[timer_id] = timer_entity
                    
                    # action_timer expiration re-establishment
                    timer_entity._unsub_expiration = async_track_point_in_time(
                        self.hass, 
                        self._async_on_expiration(timer_id), 
                        timer_data.expiration
                    )
                    new_entities.append(timer_entity)

            # add restored entities to HA UI
            if new_entities and self._async_add_entities:
                self._async_add_entities(new_entities)

    async def _save_timers(self):
        data = {tid: tdata.to_dict() for tid, tdata in self._data.items()}
        await self._store.async_save(data)

    async def create_timer_entity(self, target_entity: str, duration: int, action_config: Dict[str, Any]) -> TimerEntity:
        """Create and register a new timer entity."""
        # Generate a unique, short ID
        unique_suffix = str(uuid.uuid4())[:8]
        timer_id = f"at_{unique_suffix}" # e.g., at_a1b2c3d4       
        
        now = dt_util.now()
        expiration = now + timedelta(seconds=duration)        
        
        timer_data = TimerData(
            id = timer_id,
            entity_id=target_entity,
            duration=duration,
            action_config=action_config,
            expiration=expiration, 
            created_at=now
        )

        timer_entity = TimerEntity(timer_id, timer_data, self)

        self._data[timer_id] = timer_data
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
        _LOGGER.info("ActionTimer %s created for target %s", timer_id, target_entity)
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
        timer_entity = self._timers.pop(timer_id, None)
        self._data.pop(timer_id, None)

        if timer_entity:
            # 1. Stop the task from firing if it exists
            if timer_entity._unsub_expiration:
                timer_entity._unsub_expiration()
                timer_entity._unsub_expiration = None
            

            # 2. Remove the entity from HA
            eid = timer_entity.entity_id
            if timer_entity.hass:
                await timer_entity.async_remove()
        
            # 3. Remove from entity registry          
            registry = er.async_get(self.hass)
            if eid in registry.entities:
                registry.async_remove(eid)

        await self._save_timers()

    async def grace_period_check(self):
        """Cleanup expired timers from previous session."""
        now = dt_util.now()
        expired_timers = [tid for tid, td in self._data.items() if td.expiration <= now]
        for tid in expired_timers:
            await self.remove_timer(tid)