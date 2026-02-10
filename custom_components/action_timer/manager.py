from datetime import datetime
import logging
from typing import Dict, Any, Callable

from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.script import Script
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .models import ActionTimerData
from .sensor import ActionTimerSensor

_LOGGER = logging.getLogger(__name__)


class ActionTimerManager:
    """Manage ActionTimer entities and storage."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._store: Store[Dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, ActionTimerData] = {}
        self._tasks: Dict[str, Callable[[], None]] = {}
        self._async_add_entities : AddEntitiesCallback  | None = None

    @property
    def timers(self) -> Dict[str, ActionTimerData]:
        return self._data
    
    def setup_entity_platform(self, async_add_entities: AddEntitiesCallback) -> None:
        # Store the async_add_entities callback for later use when creating timers on the fly
        self._async_add_entities = async_add_entities
        
        # If there are already timers loaded (e.g., from storage), add them to the UI
        if self._data:
            _LOGGER.debug("Adding %s existing timers to UI", len(self._data))
            self._create_sensors_for_existing_data()

    def _create_sensors_for_existing_data(self):
        """Pushes existing data models into the Home Assistant UI."""
        sensors = [ActionTimerSensor(d) for d in self._data.values()]
        if sensors and self._async_add_entities:
            self._async_add_entities(sensors)


    async def load_and_sync(self) -> None:
        stored_data = await self._store.async_load()
        if not stored_data:
            return

        now = dt_util.now()
        initial_count = len(stored_data)

        for timer_dict in stored_data.values():
            t_data = ActionTimerData.from_dict(timer_dict)

            if t_data.expiration > now:
                self._data[t_data.id] = t_data
                self._start_timer_task(t_data)
            elif t_data.run_on_power_restore:
                _LOGGER.info("Timer %s expired during downtime, recovering", t_data.id)
                self.hass.async_create_task(self._execute_actions(t_data))             

        # Only save if we actually pruned expired timers
        if len(self._data) != initial_count:
            await self._save_to_storage()
    
        self._create_sensors_for_existing_data()

    def _start_timer_task(self, timer_data: ActionTimerData):
        """Schedules the actual Python task that waits for expiration."""
        # Use max() to handle timers that expired while HA was off (Grace Period)
        run_at = max(timer_data.expiration, dt_util.now())

        self._tasks[timer_data.id] = async_track_point_in_time(
            self.hass,
            self._async_wrap_expiration(timer_data.id),
            run_at
        )
    def _async_wrap_expiration(self, timer_id: str) -> Callable[[datetime], None]:
        """Wraps the async execution in a synchronous callback for the event helper."""
        @callback
        def _fire(now: datetime):
            if timer_id in self._data:
                self.hass.async_create_task(self._execute_and_remove(timer_id))
        return _fire
    

    async def _execute_actions(self, t_data: ActionTimerData) -> None:
        """Runs the action block using the Home Assistant script engine."""
        try:
            script_obj = Script(
                self.hass, 
                t_data.action_config, 
                f"Timer {t_data.id}", 
                DOMAIN
            )
            await script_obj.async_run(context=Context())
        except Exception as err:
            _LOGGER.error("Error executing actions for timer %s: %s", t_data.id, err)

  
    async def _execute_and_remove(self, timer_id: str) -> None:
        """Executes actions and performs cleanup."""
        t_data = self._data.get(timer_id, None)
        
        if t_data:
            await self._execute_actions(t_data)
            await self.remove_timer(timer_id)

    async def remove_timer(self, timer_id: str):
        """Cleanly remove the timer and stop background tasks."""
        # Cancel the background task (the 'Unsubscribe')
        unsub = self._tasks.pop(timer_id, None)
        if unsub:
            unsub()

        # Remove from local memory        
        self._data.pop(timer_id, None)

        # update storage
        await self._save_to_storage()

        # FIRE THE SIGNAL: This is what triggers the sensor's async_added_to_hass listener
        self.hass.bus.async_fire(f"{DOMAIN}_timer_finished", {"timer_id": timer_id})

    async def remove_all_timers(self) -> None:
        """Remove all timers, used for cleanup on unload."""
        for timer_id in list(self._data.keys()):
            await self.remove_timer(timer_id)

    async def _save_to_storage(self) -> None:
        """Serialize current state to the hidden .storage file."""
        serializable = {tid: d.to_dict() for tid, d in self._data.items()}
        await self._store.async_save(serializable)

    async def create_timer(self, duration: int, action_config: list[Dict[str, Any]], run_on_power_restore: bool = False) -> str:
        """Main entry point to start a new timer from a service call."""
        t_data = ActionTimerData(duration=duration, action_config=action_config, run_on_power_restore=run_on_power_restore)
        
        # Store Data & Start Task
        self._data[t_data.id] = t_data
        self._start_timer_task(t_data)
        
        # Push to UI
        if self._async_add_entities:
            self._async_add_entities([ActionTimerSensor(t_data)])
        
        # Persist to Disk
        await self._save_to_storage()
        
        _LOGGER.info("Started ActionTimer %s (expires: %s)", t_data.id, t_data.expiration)
        return t_data.id
    







 
  

        
     



    
 







