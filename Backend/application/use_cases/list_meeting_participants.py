"""
List Meeting Participants Use Case

Use case for listing all participants of a meeting.
"""
import logging
from typing import List, Dict
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository

logger = logging.getLogger(__name__)


class ListMeetingParticipantsUseCase:
    """Use case for listing meeting participants"""
    
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
    
    def execute(self, meeting_id: str) -> List[Dict]:
        """
        Execute listing participants.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            List of participant dictionaries
        """
        participants = self.participant_repository.find_by_meeting(meeting_id)
        
        result = []
        for participant in participants:
            result.append({
                "user_id": participant.user_id,
                "email": participant.email,
                "meeting_id": participant.meeting_id,
                "role": participant.role,
                "permissions": participant.permissions,
                "added_at": participant.added_at.isoformat(),
                "added_by": participant.added_by,
                "notifications_enabled": participant.notifications_enabled,
                "last_accessed": participant.last_accessed.isoformat() if participant.last_accessed else None,
            })
        
        logger.info(f"Listed {len(result)} participants for meeting {meeting_id}")
        
        return result

