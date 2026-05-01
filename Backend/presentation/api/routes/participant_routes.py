"""
Participant Routes

Routes for managing meeting participants.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from presentation.middleware.auth_middleware import get_current_user_id
from presentation.middleware.permission_middleware import verify_meeting_ownership, verify_meeting_access
from presentation.dto.requests import AddParticipantRequest, UpdateParticipantPermissionsRequest
from presentation.dto.responses import (
    AddParticipantResponse,
    RemoveParticipantResponse,
    UpdateParticipantPermissionsResponse,
    ParticipantListResponse,
    ParticipantResponse
)
from application.use_cases.add_participant import AddParticipantUseCase
from application.use_cases.remove_participant import RemoveParticipantUseCase
from application.use_cases.update_participant_permissions import UpdateParticipantPermissionsUseCase
from application.use_cases.list_meeting_participants import ListMeetingParticipantsUseCase
from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
from core.dependency_injection import setup_dependencies

logger = logging.getLogger(__name__)

router = APIRouter()


def create_participant_router() -> APIRouter:
    """
    Create participant router with dependencies.
    
    Returns:
        Configured APIRouter
    """
    container = setup_dependencies()
    
    # Initialize repositories
    participant_repository = RedisMeetingParticipantRepository()
    user_repository_factory = container.user_repository
    
    # Initialize use cases
    def get_add_participant_use_case():
        # Create a temporary DB session to get user repository
        db_session = container.db_session_factory()()
        try:
            user_repository = user_repository_factory(db_session)
            return AddParticipantUseCase(user_repository, participant_repository)
        finally:
            db_session.close()
    
    add_participant_use_case_factory = get_add_participant_use_case
    remove_participant_use_case = RemoveParticipantUseCase(participant_repository)
    update_permissions_use_case = UpdateParticipantPermissionsUseCase(participant_repository)
    list_participants_use_case = ListMeetingParticipantsUseCase(participant_repository)
    
    @router.post("/api/transcripts/{meeting_id}/participants", response_model=AddParticipantResponse)
    async def add_participant(
        meeting_id: str,
        request: AddParticipantRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """Add a participant to a meeting (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Add participant request for meeting {meeting_id} by user: {user_id}")
            
            # Verify ownership (only owners can add participants)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Get use case (with fresh DB session)
            add_use_case = get_add_participant_use_case()
            
            # Execute use case
            participant_data = add_use_case.execute(
                meeting_id=meeting_id,
                email=request.email,
                role=request.role,
                added_by_user_id=user_id,
                permissions=request.permissions
            )
            
            logger.info(f"Successfully added participant {request.email} to meeting {meeting_id}")
            
            return AddParticipantResponse(
                success=True,
                participant=ParticipantResponse(**participant_data),
                message=f"Participant {request.email} added successfully"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding participant: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add participant: {str(e)}"
            )
    
    @router.delete("/api/transcripts/{meeting_id}/participants/{participant_user_id}", response_model=RemoveParticipantResponse)
    async def remove_participant(
        meeting_id: str,
        participant_user_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """Remove a participant from a meeting (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            participant_user_id = unquote(participant_user_id)
            
            logger.info(f"Remove participant request for meeting {meeting_id}, participant {participant_user_id} by user: {user_id}")
            
            # Verify ownership (only owners can remove participants)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Execute use case
            removed = remove_participant_use_case.execute(meeting_id, participant_user_id, user_id)
            
            if not removed:
                raise HTTPException(
                    status_code=404,
                    detail=f"Participant {participant_user_id} not found in meeting {meeting_id}"
                )
            
            logger.info(f"Successfully removed participant {participant_user_id} from meeting {meeting_id}")
            
            return RemoveParticipantResponse(
                success=True,
                message=f"Participant removed successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing participant: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove participant: {str(e)}"
            )
    
    @router.get("/api/transcripts/{meeting_id}/participants", response_model=ParticipantListResponse)
    async def list_participants(
        meeting_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """List all participants of a meeting (requires authentication and meeting access)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"List participants request for meeting {meeting_id} by user: {user_id}")
            
            # Verify access (owner or participant can list)
            verify_meeting_access(meeting_id, user_id)
            
            # Execute use case
            participants_data = list_participants_use_case.execute(meeting_id)
            
            participants = [ParticipantResponse(**p) for p in participants_data]
            
            return ParticipantListResponse(
                participants=participants,
                count=len(participants)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing participants: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list participants: {str(e)}"
            )
    
    @router.patch("/api/transcripts/{meeting_id}/participants/{participant_user_id}/permissions", response_model=UpdateParticipantPermissionsResponse)
    async def update_participant_permissions(
        meeting_id: str,
        participant_user_id: str,
        request: UpdateParticipantPermissionsRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """Update participant permissions (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            participant_user_id = unquote(participant_user_id)
            
            logger.info(f"Update permissions request for meeting {meeting_id}, participant {participant_user_id} by user: {user_id}")
            
            # Verify ownership (only owners can update permissions)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Execute use case
            participant_data = update_permissions_use_case.execute(
                meeting_id, participant_user_id, request.permissions
            )
            
            logger.info(f"Successfully updated permissions for participant {participant_user_id} in meeting {meeting_id}")
            
            return UpdateParticipantPermissionsResponse(
                success=True,
                participant=ParticipantResponse(**participant_data),
                message="Participant permissions updated successfully"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating permissions: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update permissions: {str(e)}"
            )
    
    @router.get("/api/transcripts/{meeting_id}/participants/{participant_user_id}", response_model=ParticipantResponse)
    async def get_participant(
        meeting_id: str,
        participant_user_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """Get participant details (requires authentication and meeting access)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            participant_user_id = unquote(participant_user_id)
            
            logger.info(f"Get participant request for meeting {meeting_id}, participant {participant_user_id} by user: {user_id}")
            
            # Verify access (owner or participant can view)
            verify_meeting_access(meeting_id, user_id)
            
            # Get participant
            participant_repo = RedisMeetingParticipantRepository()
            participant = participant_repo.find_by_user_and_meeting(meeting_id, participant_user_id)
            
            if not participant:
                raise HTTPException(
                    status_code=404,
                    detail=f"Participant {participant_user_id} not found in meeting {meeting_id}"
                )
            
            return ParticipantResponse(
                user_id=participant.user_id,
                email=participant.email,
                meeting_id=participant.meeting_id,
                role=participant.role,
                permissions=participant.permissions,
                added_at=participant.added_at.isoformat(),
                added_by=participant.added_by,
                notifications_enabled=participant.notifications_enabled,
                last_accessed=participant.last_accessed.isoformat() if participant.last_accessed else None,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting participant: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get participant: {str(e)}"
            )
    
    @router.get("/api/transcripts/{meeting_id}/analytics")
    async def get_meeting_analytics(
        meeting_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """Get participation analytics for a meeting (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Get analytics request for meeting {meeting_id} by user: {user_id}")
            
            # Verify ownership (only owners can view analytics)
            from presentation.middleware.permission_middleware import verify_meeting_ownership
            verify_meeting_ownership(meeting_id, user_id)
            
            # Get analytics
            from lib.participant_analytics import get_all_participant_analytics
            analytics = get_all_participant_analytics(meeting_id)
            
            return {
                "meeting_id": meeting_id,
                "analytics": analytics,
                "participant_count": len(analytics)
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting analytics: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get analytics: {str(e)}"
            )
    
    return router

