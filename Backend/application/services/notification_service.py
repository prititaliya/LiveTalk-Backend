"""
Notification Service

Service for sending notifications to participants about meeting events.
"""
import logging
from typing import Optional
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing participant notifications"""
    
    def __init__(
        self,
        participant_repository: Optional[IMeetingParticipantRepository] = None
    ):
        """
        Initialize notification service.
        
        Args:
            participant_repository: Optional participant repository (uses Redis by default)
        """
        self.participant_repository = participant_repository or RedisMeetingParticipantRepository()
    
    def notify_participant_added(self, meeting_id: str, user_id: str, added_by_user_id: str):
        """
        Send notification when a participant is added.
        
        Args:
            meeting_id: The meeting ID
            user_id: User ID of the added participant
            added_by_user_id: User ID of the person who added them
        """
        participant = self.participant_repository.find_by_user_and_meeting(meeting_id, user_id)
        if not participant or not participant.notifications_enabled:
            return
        
        # Log notification (future: implement email/WebSocket notifications)
        logger.info(f"Notification: Participant {participant.email} was added to meeting {meeting_id} by user {added_by_user_id}")
        
        # TODO: Implement email notification
        # TODO: Implement WebSocket notification to connected clients
    
    def notify_participant_removed(self, meeting_id: str, user_id: str, removed_by_user_id: str):
        """
        Send notification when a participant is removed.
        
        Args:
            meeting_id: The meeting ID
            user_id: User ID of the removed participant
            removed_by_user_id: User ID of the person who removed them
        """
        # Log notification (future: implement email/WebSocket notifications)
        logger.info(f"Notification: Participant {user_id} was removed from meeting {meeting_id} by user {removed_by_user_id}")
        
        # TODO: Implement email notification
        # TODO: Implement WebSocket notification to connected clients
    
    def notify_meeting_update(self, meeting_id: str):
        """
        Send notification to all participants when meeting is updated.
        
        Args:
            meeting_id: The meeting ID
        """
        participants = self.participant_repository.find_by_meeting(meeting_id)
        
        for participant in participants:
            if participant.notifications_enabled:
                # Log notification (future: implement email/WebSocket notifications)
                logger.info(f"Notification: Meeting {meeting_id} was updated, notifying participant {participant.email}")
        
        # TODO: Implement email notification
        # TODO: Implement WebSocket notification to connected clients

