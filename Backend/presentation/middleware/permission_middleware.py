"""
Permission Middleware

Middleware for checking meeting access permissions in API routes.
"""
import logging
from typing import Dict, Optional
from fastapi import HTTPException, Depends
from presentation.middleware.auth_middleware import get_current_user_id
from application.services.permission_service import PermissionService
from lib.transcript_storage import get_transcript

logger = logging.getLogger(__name__)


def verify_meeting_access(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    permission_service: Optional[PermissionService] = None
) -> Dict:
    """
    Verify that a user has access to a meeting (owner or participant).
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID from authentication
        permission_service: Optional permission service (uses default if not provided)
        
    Returns:
        Transcript data dictionary
        
    Raises:
        HTTPException: 404 if meeting not found, 403 if user has no access
    """
    if permission_service is None:
        permission_service = PermissionService()
    
    logger.info(f"Verifying meeting access for meeting_id: {meeting_id}, user_id: {user_id}")
    
    # Get meeting data
    transcript_data = get_transcript(meeting_id)
    
    if not transcript_data:
        logger.warning(f"Meeting not found: {meeting_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    # Check access
    if not permission_service.can_access_meeting(meeting_id, user_id):
        logger.warning(f"Access denied for meeting_id: {meeting_id}, user_id: {user_id}")
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this meeting"
        )
    
    # Track access for analytics (only for participants, not owners)
    if not permission_service.is_owner(meeting_id, user_id):
        try:
            from lib.participant_analytics import track_participant_access
            from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
            track_participant_access(meeting_id, user_id)
            # Also update last_accessed in participant repository
            participant_repo = RedisMeetingParticipantRepository()
            participant_repo.update_last_accessed(meeting_id, user_id)
        except Exception as e:
            logger.warning(f"Failed to track participant access: {e}")
    
    logger.info(f"Access verified for meeting_id: {meeting_id}, user_id: {user_id}")
    return transcript_data


def verify_meeting_ownership(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    permission_service: Optional[PermissionService] = None
) -> Dict:
    """
    Verify that a user is the owner of a meeting (required for modification operations).
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID from authentication
        permission_service: Optional permission service (uses default if not provided)
        
    Returns:
        Transcript data dictionary
        
    Raises:
        HTTPException: 404 if meeting not found, 403 if user is not the owner
    """
    if permission_service is None:
        permission_service = PermissionService()
    
    logger.info(f"Verifying meeting ownership for meeting_id: {meeting_id}, user_id: {user_id}")
    
    # Get meeting data
    transcript_data = get_transcript(meeting_id)
    
    if not transcript_data:
        logger.warning(f"Meeting not found: {meeting_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    # Check ownership
    if not permission_service.is_owner(meeting_id, user_id):
        logger.warning(f"Ownership denied for meeting_id: {meeting_id}, user_id: {user_id}")
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to modify this meeting"
        )
    
    logger.info(f"Ownership verified for meeting_id: {meeting_id}, user_id: {user_id}")
    return transcript_data


def verify_meeting_permission(
    meeting_id: str,
    permission: str,
    user_id: str = Depends(get_current_user_id),
    permission_service: Optional[PermissionService] = None
) -> Dict:
    """
    Verify that a user has a specific permission for a meeting.
    
    Args:
        meeting_id: The meeting ID
        permission: The permission to check (e.g., "can_view_transcript", "can_use_chatbot")
        user_id: The user ID from authentication
        permission_service: Optional permission service (uses default if not provided)
        
    Returns:
        Transcript data dictionary
        
    Raises:
        HTTPException: 404 if meeting not found, 403 if user doesn't have the permission
    """
    if permission_service is None:
        permission_service = PermissionService()
    
    logger.info(f"Verifying permission '{permission}' for meeting_id: {meeting_id}, user_id: {user_id}")
    
    # Get meeting data
    transcript_data = get_transcript(meeting_id)
    
    if not transcript_data:
        logger.warning(f"Meeting not found: {meeting_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    # Check permission
    if not permission_service.has_permission(meeting_id, user_id, permission):
        logger.warning(f"Permission '{permission}' denied for meeting_id: {meeting_id}, user_id: {user_id}")
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to {permission.replace('_', ' ')} for this meeting"
        )
    
    logger.info(f"Permission '{permission}' verified for meeting_id: {meeting_id}, user_id: {user_id}")
    return transcript_data

