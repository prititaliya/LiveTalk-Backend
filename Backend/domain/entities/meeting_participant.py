"""
Meeting Participant Entity

Represents a post-meeting participant with permissions and access rights.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class MeetingParticipant:
    """A post-meeting participant entity"""
    user_id: str
    email: str
    meeting_id: str
    role: str  # "viewer" or "collaborator"
    added_at: datetime
    added_by: str  # User ID of meeting owner who added them
    permissions: Dict[str, bool] = field(default_factory=dict)
    notifications_enabled: bool = True
    last_accessed: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate participant data"""
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.email:
            raise ValueError("Email cannot be empty")
        if not self.meeting_id:
            raise ValueError("Meeting ID cannot be empty")
        if self.role not in ["viewer", "collaborator"]:
            raise ValueError("Role must be 'viewer' or 'collaborator'")
        if not isinstance(self.added_at, datetime):
            raise ValueError("Added at must be a datetime object")
        
        # Set default permissions based on role
        if not self.permissions:
            self.permissions = self._get_default_permissions()
    
    def _get_default_permissions(self) -> Dict[str, bool]:
        """Get default permissions based on role"""
        if self.role == "viewer":
            return {
                "can_view_transcript": True,
                "can_use_chatbot": True,
                "can_view_summaries": True,
                "can_annotate": False,
                "can_comment": False,
            }
        else:  # collaborator
            return {
                "can_view_transcript": True,
                "can_use_chatbot": True,
                "can_view_summaries": True,
                "can_annotate": True,
                "can_comment": True,
            }
    
    def has_permission(self, permission: str) -> bool:
        """Check if participant has a specific permission"""
        return self.permissions.get(permission, False)
    
    def update_permission(self, permission: str, value: bool):
        """Update a specific permission"""
        # Validate permission key
        valid_permissions = [
            "can_view_transcript",
            "can_use_chatbot",
            "can_view_summaries",
            "can_annotate",
            "can_comment",
        ]
        if permission not in valid_permissions:
            raise ValueError(f"Invalid permission: {permission}")
        
        # Enforce role-based restrictions
        if self.role == "viewer" and permission in ["can_annotate", "can_comment"]:
            raise ValueError(f"Viewers cannot have {permission} permission")
        
        self.permissions[permission] = value
    
    def update_last_accessed(self):
        """Update the last accessed timestamp"""
        self.last_accessed = datetime.now()
    
    def __eq__(self, other):
        """Check equality based on user_id and meeting_id"""
        if not isinstance(other, MeetingParticipant):
            return False
        return self.user_id == other.user_id and self.meeting_id == other.meeting_id
    
    def __hash__(self):
        """Make MeetingParticipant hashable"""
        return hash((self.user_id, self.meeting_id))

