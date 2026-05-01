"""
Remote Session Entity

Domain entity representing a remote recording control session.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set


@dataclass
class RemoteSession:
    """A remote recording control session"""
    session_id: str
    user_id: str
    room_name: str
    created_at: datetime
    expires_at: datetime
    status: str  # 'pending', 'active', 'expired'
    connected_devices: Set[str] = None  # Set of 'laptop', 'mobile', or both
    recording_state: str = "idle"  # 'idle', 'recording', 'paused', 'stopped'
    session_token: Optional[str] = None
    
    def __post_init__(self):
        """Validate remote session data"""
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.room_name:
            raise ValueError("Room name cannot be empty")
        if not isinstance(self.created_at, datetime):
            raise ValueError("Created at must be a datetime object")
        if not isinstance(self.expires_at, datetime):
            raise ValueError("Expires at must be a datetime object")
        if self.status not in ['pending', 'active', 'expired']:
            raise ValueError(f"Invalid status: {self.status}. Must be 'pending', 'active', or 'expired'")
        if self.recording_state not in ['idle', 'recording', 'paused', 'stopped']:
            raise ValueError(f"Invalid recording state: {self.recording_state}. Must be 'idle', 'recording', 'paused', or 'stopped'")
        
        if self.connected_devices is None:
            self.connected_devices = set()
    
    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.now() >= self.expires_at
    
    def is_active(self) -> bool:
        """Check if the session is active"""
        return self.status == 'active' and not self.is_expired()
    
    def can_connect(self) -> bool:
        """Check if a device can connect to this session"""
        return self.status in ['pending', 'active'] and not self.is_expired()
    
    def add_device(self, device: str) -> None:
        """Add a connected device"""
        if device not in ['laptop', 'mobile']:
            raise ValueError(f"Invalid device type: {device}. Must be 'laptop' or 'mobile'")
        self.connected_devices.add(device)
        if self.status == 'pending' and len(self.connected_devices) > 0:
            self.status = 'active'
    
    def remove_device(self, device: str) -> None:
        """Remove a connected device"""
        self.connected_devices.discard(device)
        if len(self.connected_devices) == 0:
            self.status = 'expired'
    
    def has_device(self, device: str) -> bool:
        """Check if a device is connected"""
        return device in self.connected_devices
    
    def __eq__(self, other):
        """Check equality based on session_id"""
        if not isinstance(other, RemoteSession):
            return False
        return self.session_id == other.session_id
    
    def __hash__(self):
        """Make RemoteSession hashable"""
        return hash(self.session_id)

