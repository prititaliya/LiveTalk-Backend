"""
Update Participant Permissions Use Case

Use case for updating participant permissions.
"""
import logging
from typing import Dict
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository

logger = logging.getLogger(__name__)


class UpdateParticipantPermissionsUseCase:
    """Use case for updating participant permissions"""
    
    def __init__(
        self,
        participant_repository: IMeetingParticipantRepository = None
    ):
        """
        Initialize use case.
        
        Args:
            participant_repository: Optional participant repository (uses Redis by default)
        """
        self.participant_repository = participant_repository or RedisMeetingParticipantRepository()
    
    def execute(
        self,
        meeting_id: str,
        user_id: str,
        permissions: Dict[str, bool]
    ) -> Dict:
        """
        Execute updating participant permissions.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID of the participant
            permissions: Dictionary of permission updates
            
        Returns:
            Dictionary with updated participant information
            
        Raises:
            ValueError: If participant not found or validation fails
        """
        # Check if participant exists
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if not participant:
            raise ValueError(f"Participant {user_id} not found in meeting {meeting_id}")
        
        # Update permissions
        updated_participant = self.participant_repository.update_permissions(
            meeting_id, user_id, permissions
        )
        
        if not updated_participant:
            raise ValueError(f"Failed to update permissions for participant {user_id}")
        
        logger.info(f"Updated permissions for participant {user_id} in meeting {meeting_id}")
        
        return {
            "user_id": updated_participant.user_id,
            "email": updated_participant.email,
            "meeting_id": updated_participant.meeting_id,
            "role": updated_participant.role,
            "permissions": updated_participant.permissions,
            "added_at": updated_participant.added_at.isoformat(),
            "added_by": updated_participant.added_by,
            "notifications_enabled": updated_participant.notifications_enabled,
            "last_accessed": updated_participant.last_accessed.isoformat() if updated_participant.last_accessed else None,
        }

