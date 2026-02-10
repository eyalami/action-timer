from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict
import uuid

from homeassistant.util import dt as dt_util

from .const import ID, DURATION, CREATED_AT, EXPIRATION, ACTION_CONFIG, RUN_ON_POWER_RESTORE

@dataclass
class ActionTimerData:
    duration: int                       # The countdown length (in seconds)
    action_config: list[Dict[str, Any]] # action configuration as returned by HA action picker
    run_on_power_restore: bool = False  # Whether to run the action if HA restarts while timer is active

    id: str = field(default_factory=lambda: f"at_{str(uuid.uuid4())[:8]}")     # Unique timer ID (e.g., "at_a1b2c3d4") 
    created_at: datetime = field(default_factory=dt_util.now)                   # When the timer was created
    expiration: datetime = field(init=False)                                    # When it ends (calculated from created_at + duration)
    
    def __post_init__(self):
        if not hasattr(self, EXPIRATION):
            self.expiration = self.created_at + timedelta(seconds=self.duration)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            ID: self.id,
            DURATION: self.duration,
            EXPIRATION: self.expiration.isoformat(),
            ACTION_CONFIG: self.action_config,
            CREATED_AT: self.created_at.isoformat(),
            RUN_ON_POWER_RESTORE: self.run_on_power_restore
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionTimerData":
        """Create instance from dictionary with type-safe datetime parsing."""
        
        # Parse datetimes with fallbacks to ensure type safety
        created_at = dt_util.parse_datetime(data[CREATED_AT]) or dt_util.now()
        expiration = dt_util.parse_datetime(data[EXPIRATION]) or (created_at + timedelta(seconds=data[DURATION]))

        instance = cls(
            duration=data[DURATION],
            action_config=data.get(ACTION_CONFIG, []),
            run_on_power_restore=data.get(RUN_ON_POWER_RESTORE, False),
            id=data[ID],
            created_at=created_at
        )
        
        instance.expiration = expiration
        return instance
    
    