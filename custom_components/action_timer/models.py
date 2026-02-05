from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class TimerData:
    """Data model for timer entities"""
    id: str
    entity_id: str
    duration: int
    action_config: Dict[str, Any]
    expiration: datetime
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def remaining_seconds(self) -> int:
        """Calculate remaining seconds until expiration"""
        return max(0, int((self.expiration - datetime.now()).total_seconds()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "duration": self.duration,
            "action_config": self.action_config,
            "expiration": self.expiration.isoformat(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimerData":
        """Create instance from dictionary"""
        return cls(
            id=data["id"],
            entity_id=data["entity_id"],
            duration=data["duration"],
            action_config=data["action_config"],
            expiration=datetime.fromisoformat(data["expiration"]),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
