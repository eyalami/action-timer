from homeassistant.helpers.storage import Store
from .models import TimerData

class TimerStore:
    """Versioned storage for timer data."""

    def __init__(self, hass):
        """Initialize the timer store."""
        self._store = Store(hass, 1, f"{TimerStore.__module__}.storage")

    async def async_load_timers(self):
        """Load all timers from storage."""
        if (data := await self._store.async_load()) is not None:
            return {timer_id: TimerData.from_dict(timer_data) 
                   for timer_id, timer_data in data.items()}
        return {}

    async def async_save_timers(self, timers):
        """Save timers to storage."""
        data = {timer_id: timer_data.to_dict() 
                for timer_id, timer_data in timers.items()}
        await self._store.async_save(data)

    async def async_delete_timer(self, timer_id):
        """Delete a specific timer."""
        timers = await self.async_load_timers()
        if timer_id in timers:
            del timers[timer_id]
            await self.async_save_timers(timers)