from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class TimerData:
    """Data model for timer entities"""
    entity_id: str
    duration: int
    service_to_call: str
    expiration: datetime
    version: int = 1
    created_at: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None

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
            "entity_id": self.entity_id,
            "duration": self.duration,
            "service_to_call": self.service_to_call,
            "expiration": self.expiration.isoformat(),
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimerData":
        """Create instance from dictionary"""
        return cls(
            entity_id=data["entity_id"],
            duration=data["duration"],
            service_to_call=data["service_to_call"],
            expiration=datetime.fromisoformat(data["expiration"]),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            context=data.get("context")
        )