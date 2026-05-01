"""
Meeting ID Value Object

Immutable value object representing a unique meeting identifier.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MeetingId:
    """Immutable meeting identifier"""
    value: str
    
    def __post_init__(self):
        """Validate meeting ID format"""
        if not self.value:
            raise ValueError("Meeting ID cannot be empty")
        if not isinstance(self.value, str):
            raise ValueError("Meeting ID must be a string")
    
    @classmethod
    def generate(cls, room_name: str, timestamp: Optional[datetime] = None) -> "MeetingId":
        """
        Generate a meeting ID from room name and timestamp.
        
        Args:
            room_name: The room name
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            MeetingId instance
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Format timestamp
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Clean room name
        safe_room_name = "".join(
            c for c in room_name if c.isalnum() or c in ("-", "_")
        ).strip().replace(" ", "_")
        
        meeting_id_value = f"{safe_room_name}_{timestamp_str}"
        return cls(meeting_id_value)
    
    def __str__(self) -> str:
        """String representation"""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation"""
        return f"MeetingId('{self.value}')"

