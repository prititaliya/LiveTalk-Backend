"""
Add Participant Use Case

Use case for adding a participant to a meeting.
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from domain.entities.meeting_participant import MeetingParticipant
from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from domain.interfaces.user_repository import IUserRepository
from application.services.participant_validation_service import ParticipantValidationService
from application.services.notification_service import NotificationService
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
from lib.transcript_storage import update_meeting_participant_count

logger = logging.getLogger(__name__)


class AddParticipantUseCase:
    """Use case for adding a participant to a meeting"""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        participant_repository: Optional[IMeetingParticipantRepository] = None,
        validation_service: Optional[ParticipantValidationService] = None
    ):
        """
        Initialize use case.
        
        Args:
            user_repository: User repository for finding users by email
            participant_repository: Optional participant repository (uses Redis by default)
            validation_service: Optional validation service (creates new if not provided)
        """
        self.user_repository = user_repository
        self.participant_repository = participant_repository or RedisMeetingParticipantRepository()
        self.validation_service = validation_service or ParticipantValidationService(user_repository, self.participant_repository)
        self.notification_service = NotificationService(self.participant_repository)
    
    def execute(
        self,
        meeting_id: str,
        email: str,
        role: str,
        added_by_user_id: str,
        permissions: Optional[Dict[str, bool]] = None
    ) -> Dict:
        """
        Execute adding a participant.
        
        Args:
            meeting_id: The meeting ID
            email: Email address of the participant
            role: Participant role ("viewer" or "collaborator")
            added_by_user_id: User ID of the person adding the participant
            permissions: Optional custom permissions (defaults based on role if not provided)
            
        Returns:
            Dictionary with participant information
            
        Raises:
            ValueError: If validation fails
        """
        # Normalize email
        email = email.lower().strip()
        
        # Validate
        is_valid, error_message = self.validation_service.validate_add_participant(
            meeting_id, email, added_by_user_id
        )
        if not is_valid:
            raise ValueError(error_message)
        
        # Find user by email
        user = self.user_repository.find_by_email(email)
        if not user:
            raise ValueError(f"User with email '{email}' not found")
        
        # Validate role
        if role not in ["viewer", "collaborator"]:
            raise ValueError("Role must be 'viewer' or 'collaborator'")
        
        # Create participant entity
        participant = MeetingParticipant(
            user_id=user.id,
            email=email,
            meeting_id=meeting_id,
            role=role,
            added_at=datetime.now(),
            added_by=added_by_user_id,
            permissions=permissions,  # Will use defaults if None
            notifications_enabled=True,
            last_accessed=None,
        )
        
        # If custom permissions provided, apply them
        if permissions:
            for perm, value in permissions.items():
                try:
                    participant.update_permission(perm, value)
                except ValueError as e:
                    logger.warning(f"Invalid permission '{perm}': {e}")
        
        # Add participant
        added_participant = self.participant_repository.add(participant)
        
        # Record addition for rate limiting
        self.validation_service.record_participant_addition(added_by_user_id)
        
        # Update participant count in meeting
        update_meeting_participant_count(meeting_id)
        
        # Send notification
        self.notification_service.notify_participant_added(meeting_id, user.id, added_by_user_id)
        
        logger.info(f"Added participant {email} to meeting {meeting_id} with role {role}")
        
        return {
            "user_id": added_participant.user_id,
            "email": added_participant.email,
            "meeting_id": added_participant.meeting_id,
            "role": added_participant.role,
            "permissions": added_participant.permissions,
            "added_at": added_participant.added_at.isoformat(),
            "added_by": added_participant.added_by,
            "notifications_enabled": added_participant.notifications_enabled,
            "last_accessed": added_participant.last_accessed.isoformat() if added_participant.last_accessed else None,
        }

