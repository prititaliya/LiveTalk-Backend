"""
Permission Service

Service for checking meeting access permissions and participant rights.
"""
from typing import Optional, Dict
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
from lib.transcript_storage import get_transcript


class PermissionService:
    """Service for managing meeting permissions and access control"""
    
    def __init__(self, participant_repository: Optional[IMeetingParticipantRepository] = None):
        """
        Initialize permission service.
        
        Args:
            participant_repository: Optional participant repository (uses Redis by default)
        """
        self.participant_repository = participant_repository or RedisMeetingParticipantRepository()
    
    def can_access_meeting(self, meeting_id: str, user_id: str) -> bool:
        """
        Check if a user can access a meeting (owner or participant).
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID to check
            
        Returns:
            True if user can access the meeting, False otherwise
        """
        # Get meeting data
        meeting_data = get_transcript(meeting_id)
        if not meeting_data:
            return False
        
        # Check if user is the owner
        meeting_user_id = meeting_data.get("user_id")
        if meeting_user_id and str(meeting_user_id).strip() == str(user_id).strip():
            return True
        
        # Check if user is a participant
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if participant:
            return True
        
        return False
    
    def is_owner(self, meeting_id: str, user_id: str) -> bool:
        """
        Check if a user is the owner of a meeting.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID to check
            
        Returns:
            True if user is the owner, False otherwise
        """
        meeting_data = get_transcript(meeting_id)
        if not meeting_data:
            return False
        
        meeting_user_id = meeting_data.get("user_id")
        if meeting_user_id:
            return str(meeting_user_id).strip() == str(user_id).strip()
        
        return False
    
    def has_permission(self, meeting_id: str, user_id: str, permission: str) -> bool:
        """
        Check if a user has a specific permission for a meeting.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID to check
            permission: The permission to check (e.g., "can_view_transcript", "can_use_chatbot")
            
        Returns:
            True if user has the permission, False otherwise
        """
        # Owners have all permissions
        if self.is_owner(meeting_id, user_id):
            return True
        
        # Check participant permissions
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if participant:
            return participant.has_permission(permission)
        
        return False
    
    def can_view_transcript(self, meeting_id: str, user_id: str) -> bool:
        """Check if user can view transcript"""
        return self.has_permission(meeting_id, user_id, "can_view_transcript")
    
    def can_use_chatbot(self, meeting_id: str, user_id: str) -> bool:
        """Check if user can use chatbot"""
        return self.has_permission(meeting_id, user_id, "can_use_chatbot")
    
    def can_view_summaries(self, meeting_id: str, user_id: str) -> bool:
        """Check if user can view summaries"""
        return self.has_permission(meeting_id, user_id, "can_view_summaries")
    
    def can_annotate(self, meeting_id: str, user_id: str) -> bool:
        """Check if user can annotate (collaborators only)"""
        return self.has_permission(meeting_id, user_id, "can_annotate")
    
    def can_comment(self, meeting_id: str, user_id: str) -> bool:
        """Check if user can comment (collaborators only)"""
        return self.has_permission(meeting_id, user_id, "can_comment")
    
    def can_modify_meeting(self, meeting_id: str, user_id: str) -> bool:
        """
        Check if user can modify meeting (only owners can modify).
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID to check
            
        Returns:
            True if user is the owner, False otherwise
        """
        return self.is_owner(meeting_id, user_id)
    
    def get_user_role(self, meeting_id: str, user_id: str) -> Optional[str]:
        """
        Get the user's role for a meeting (owner, collaborator, viewer, or None).
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID
            
        Returns:
            Role string or None if user has no access
        """
        if self.is_owner(meeting_id, user_id):
            return "owner"
        
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if participant:
            return participant.role
        
        return None

