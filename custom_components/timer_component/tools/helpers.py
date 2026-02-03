import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import async_call_from_config

_LOGGER = logging.getLogger(__name__)

def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration."""
    periods = [
        ('year', 60*60*24*365),
        ('month', 60*60*24*30),
        ('day', 60*60*24),
        ('hour', 60*60),
        ('minute', 60),
        ('second', 1)
    ]
    parts = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            parts.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    return ", ".join(parts[:2]) if parts else "0 seconds"

async def safe_service_call(
    hass: HomeAssistant,
    service_data: Dict[str, Any],
    context: Dict[str, Any] = None
) -> bool:
    """Make a safe service call with error handling."""
    try:
        await async_call_from_config(
            hass,
            service_data,
            blocking=True,
            context=context
        )
        return True
    except Exception as e:
        _LOGGER.error("Service call failed: %s", str(e))
        return False

def validate_entity_id(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate if an entity ID exists in the system."""
    return hass.states.get(entity_id) is not None

def calculate_expiration(duration: int) -> datetime:
    """Calculate expiration datetime from now."""
    return datetime.now() + timedelta(seconds=duration)