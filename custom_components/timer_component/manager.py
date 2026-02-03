import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import slugify

from .const import DOMAIN, SERVICE_TURN_OFF, SERVICE_SET_TIMER, SERVICE_CANCEL_TIMER
from .models import TimerData

_LOGGER = logging.getLogger(__name__)
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1

class TimerEntity(Entity):
    """Representation of a Timer entity."""

    def __init__(self, timer_data: TimerData):
        """Initialize the timer."""
        self._timer_data = timer_data
        self._unsub_expiration = None

    @property
    def name(self) -> str:
        """Return the name of the timer."""
        return f"Timer for {self._timer_data.entity_id}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._timer_data.entity_id}_{self._timer_data.created_at.timestamp()}"

    @property
    def state(self) -> str:
        """Return the state of the timer."""
        return str(self._timer_data.remaining_seconds)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {
            "target_entity": self._timer_data.entity_id,
            "service_to_call": self._timer_data.service_to_call,
            "expiration": self._timer_data.expiration.isoformat(),
            "created_at": self._timer_data.created_at.isoformat()
        }

class TimerManager:
    """Manage timer entities and storage."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the timer manager."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._timers: Dict[str, TimerEntity] = {}
        self._data: Dict[str, TimerData] = {}

    async def async_added_to_hass(self):
        """Handle when added to Home Assistant."""
        await self._load_timers()
        await self.grace_period_check()

    async def _load_timers(self):
        """Load timers from storage."""
        if (data := await self._store.async_load()) is not None:
            for timer_id, timer_data in data.items():
                self._data[timer_id] = TimerData.from_dict(timer_data)

    async def _save_timers(self):
        """Save timers to storage."""
        data = {timer_id: timer_data.to_dict() 
                for timer_id, timer_data in self._data.items()}
        await self._store.async_save(data)

    async def create_timer_entity(self, target_entity: str, duration: int, 
                                service_to_call: str = SERVICE_TURN_OFF) -> TimerEntity:
        """Create and register a new timer entity."""
        timer_id = f"{slugify(target_entity)}_{datetime.now().timestamp()}"
        expiration = datetime.now() + timedelta(seconds=duration)
        
        timer_data = TimerData(
            entity_id=target_entity,
            duration=duration,
            service_to_call=service_to_call,
            expiration=expiration
        )
        
        timer_entity = TimerEntity(timer_data)
        self._timers[timer_id] = timer_entity
        self._data[timer_id] = timer_data
        
        timer_entity._unsub_expiration = async_track_point_in_time(
            self.hass, 
            self._async_on_expiration(timer_id), 
            expiration
        )
        
        timer_entity.async_write_ha_state()
        await self._save_timers()
        return timer_entity

    @callback
    def _async_on_expiration(self, timer_id: str):
        """Handle timer expiration."""
        async def _async_expired(now: datetime):
            await self._async_execute_and_remove(timer_id)
        return _async_expired

    async def _async_execute_and_remove(self, timer_id: str):
        """Execute service call and remove timer."""
        timer_data = self._data.get(timer_id)
        if timer_data is None:
            return

        await self.hass.services.async_call(
            domain="homeassistant",
            service="turn_off",
            service_data={"entity_id": timer_data.entity_id},
            blocking=True
        )
        
        await self.remove_timer(timer_id)

    async def remove_timer(self, timer_id: str):
        """Remove a timer."""
        if timer_entity := self._timers.pop(timer_id, None):
            if timer_entity._unsub_expiration:
                timer_entity._unsub_expiration()
            timer_entity.async_remove()
        
        if timer_id in self._data:
            del self._data[timer_id]
        
        await self._save_timers()

    async def grace_period_check(self):
        """Check for expired timers from previous session."""
        now = datetime.now()
        expired_timers = [
            timer_id for timer_id, timer_data in self._data.items()
            if timer_data.expiration <= now
        ]
        
        for timer_id in expired_timers:
            await self.remove_timer(timer_id)