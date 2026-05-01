"""
Remove Participant Use Case

Use case for removing a participant from a meeting.
"""
import logging
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from application.services.notification_service import NotificationService
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
from lib.transcript_storage import update_meeting_participant_count

logger = logging.getLogger(__name__)


class RemoveParticipantUseCase:
    """Use case for removing a participant from a meeting"""
    
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
        self.notification_service = NotificationService(self.participant_repository)
    
    def execute(self, meeting_id: str, user_id: str, removed_by_user_id: str = None) -> bool:
        """
        Execute removing a participant.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID of the participant to remove
            removed_by_user_id: The user ID who is removing the participant (optional, for notifications)
            
        Returns:
            True if removed successfully, False if not found
            
        Raises:
            ValueError: If meeting doesn't exist or validation fails
        """
        # Check if participant exists
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if not participant:
            return False
        
        # Remove participant
        removed = self.participant_repository.remove(meeting_id, user_id)
        
        if removed:
            # Update participant count in meeting
            update_meeting_participant_count(meeting_id)
            
            # Send notification if removed_by_user_id is provided
            if removed_by_user_id:
                self.notification_service.notify_participant_removed(meeting_id, user_id, removed_by_user_id)
            
            logger.info(f"Removed participant {user_id} from meeting {meeting_id}")
        
        return removed

