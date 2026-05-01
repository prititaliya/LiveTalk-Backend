"""
Participant Validation Service

Service for validating participant additions with business logic checks.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from domain.interfaces.user_repository import IUserRepository
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
from lib.transcript_storage import get_transcript
from infrastructure.config.redis_config import get_redis_client

logger = logging.getLogger(__name__)


class ParticipantValidationService:
    """Service for validating participant additions"""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        participant_repository: Optional[IMeetingParticipantRepository] = None
    ):
        """
        Initialize validation service.
        
        Args:
            user_repository: User repository for checking user existence
            participant_repository: Optional participant repository (uses Redis by default)
        """
        self.user_repository = user_repository
        self.participant_repository = participant_repository or RedisMeetingParticipantRepository()
        self.max_participants_per_hour = 50  # Rate limit: max 50 participants per hour per user
    
    def validate_email_exists(self, email: str) -> bool:
        """
        Validate that a user with the email exists in the database.
        
        Args:
            email: Email address to check
            
        Returns:
            True if user exists, False otherwise
        """
        user = self.user_repository.find_by_email(email.lower().strip())
        return user is not None
    
    def validate_user_account_status(self, email: str) -> bool:
        """
        Validate that a user account is active (not suspended/deleted).
        Currently all existing users are considered active.
        Future: Add account status field to User entity if needed.
        
        Args:
            email: Email address to check
            
        Returns:
            True if account is active, False otherwise
        """
        user = self.user_repository.find_by_email(email.lower().strip())
        if not user:
            return False
        
        # Currently all users are considered active
        # Future: Check user.status == "active" if status field is added
        return True
    
    def validate_not_already_participant(self, meeting_id: str, email: str) -> bool:
        """
        Validate that the user is not already a participant.
        
        Args:
            meeting_id: The meeting ID
            email: Email address to check
            
        Returns:
            True if not already a participant, False otherwise
        """
        user = self.user_repository.find_by_email(email.lower().strip())
        if not user:
            return False
        
        existing = self.participant_repository.find_by_user_and_meeting(meeting_id, user.id)
        return existing is None
    
    def validate_meeting_exists(self, meeting_id: str) -> bool:
        """
        Validate that the meeting exists.
        
        Args:
            meeting_id: The meeting ID to check
            
        Returns:
            True if meeting exists, False otherwise
        """
        meeting_data = get_transcript(meeting_id)
        return meeting_data is not None
    
    def validate_meeting_completed(self, meeting_id: str) -> bool:
        """
        Validate that the meeting has ended (has end_time).
        
        Args:
            meeting_id: The meeting ID to check
            
        Returns:
            True if meeting is completed, False otherwise
        """
        meeting_data = get_transcript(meeting_id)
        if not meeting_data:
            return False
        
        end_time = meeting_data.get("end_time")
        return end_time is not None and end_time != ""
    
    def validate_rate_limit(self, user_id: str) -> bool:
        """
        Validate rate limiting for adding participants.
        
        Args:
            user_id: The user ID who is adding participants
            
        Returns:
            True if within rate limit, False otherwise
        """
        client = get_redis_client()
        
        # Get current hour timestamp
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        hour_key = current_hour.strftime("%Y%m%d%H")
        
        rate_limit_key = f"rate_limit:add_participant:{user_id}:{hour_key}"
        
        # Get current count
        count = client.get(rate_limit_key)
        if count is None:
            count = 0
        else:
            count = int(count)
        
        # Check if limit exceeded
        if count >= self.max_participants_per_hour:
            logger.warning(f"Rate limit exceeded for user {user_id}: {count} participants added in current hour")
            return False
        
        return True
    
    def record_participant_addition(self, user_id: str):
        """
        Record that a participant was added (for rate limiting).
        
        Args:
            user_id: The user ID who added the participant
        """
        client = get_redis_client()
        
        # Get current hour timestamp
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        hour_key = current_hour.strftime("%Y%m%d%H")
        
        rate_limit_key = f"rate_limit:add_participant:{user_id}:{hour_key}"
        
        # Increment count (expires in 2 hours to be safe)
        client.incr(rate_limit_key)
        client.expire(rate_limit_key, 7200)  # 2 hours
    
    def validate_add_participant(
        self,
        meeting_id: str,
        email: str,
        added_by_user_id: str
    ):
        """
        Comprehensive validation for adding a participant.
        
        Args:
            meeting_id: The meeting ID
            email: Email address of the participant
            added_by_user_id: User ID of the person adding the participant
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate meeting exists
        if not self.validate_meeting_exists(meeting_id):
            return False, "Meeting not found"
        
        # Validate meeting is completed
        if not self.validate_meeting_completed(meeting_id):
            return False, "Participants can only be added to completed meetings"
        
        # Validate email exists
        if not self.validate_email_exists(email):
            return False, f"User with email '{email}' is not registered. Users must be registered before being added as participants."
        
        # Get user by email to check their user_id
        user = self.user_repository.find_by_email(email.lower().strip())
        if not user:
            return False, f"User with email '{email}' is not registered. Users must be registered before being added as participants."
        
        # Validate that the user is not the meeting owner
        meeting_data = get_transcript(meeting_id)
        if meeting_data:
            meeting_owner_id = meeting_data.get("user_id")
            if meeting_owner_id and str(meeting_owner_id).strip() == str(user.id).strip():
                return False, "You cannot add yourself as a participant. As the meeting owner, you already have full access to this meeting."
        
        # Validate account is active
        if not self.validate_user_account_status(email):
            return False, f"User account with email '{email}' is not active"
        
        # Validate not already a participant
        if not self.validate_not_already_participant(meeting_id, email):
            return False, f"User with email '{email}' is already a participant in this meeting"
        
        # Validate rate limit
        if not self.validate_rate_limit(added_by_user_id):
            return False, "Rate limit exceeded. Too many participants added in a short time. Please try again later."
        
        return True, None

