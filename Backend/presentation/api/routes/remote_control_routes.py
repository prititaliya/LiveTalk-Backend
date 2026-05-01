"""
Remote Control Routes

Routes for remote recording control session management.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from presentation.dto.remote_session_dto import (
    GenerateSessionRequest,
    GenerateSessionResponse,
    SessionStatusResponse,
    RemoteCommandRequest,
    RemoteCommandResponse
)
from presentation.middleware.auth_middleware import get_current_user_id
from application.use_cases.generate_remote_session import GenerateRemoteSessionUseCase
from application.services.remote_control_service import RemoteControlService

logger = logging.getLogger(__name__)

router = APIRouter()


def create_remote_control_router(
    generate_remote_session_use_case: GenerateRemoteSessionUseCase,
    remote_control_service: RemoteControlService
) -> APIRouter:
    """
    Create remote control router with dependencies.
    
    Args:
        generate_remote_session_use_case: Use case for generating remote sessions
        remote_control_service: Service for remote control operations
        
    Returns:
        Configured APIRouter
    """
    
    @router.post("/api/remote/generate-session", response_model=GenerateSessionResponse)
    async def generate_session(
        request: GenerateSessionRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """
        Generate a remote session with QR code.
        Requires authentication.
        """
        try:
            # Use user_id from JWT if not provided in request
            effective_user_id = request.user_id or user_id
            
            result = generate_remote_session_use_case.execute(
                user_id=effective_user_id,
                room_name=request.room_name
            )
            return GenerateSessionResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error generating remote session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate remote session: {str(e)}"
            )
    
    @router.get("/api/remote/session/{session_token}", response_model=SessionStatusResponse)
    async def get_session_status(session_token: str):
        """
        Get session status by token.
        Used by mobile web app on initial load.
        """
        try:
            session = remote_control_service.validate_remote_session(session_token)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found or expired"
                )
            
            recording_state = remote_control_service.get_recording_state(session.session_id)
            
            return SessionStatusResponse(
                room_name=session.room_name,
                status=session.status,
                recording_state=recording_state,
                expires_at=session.expires_at.isoformat(),
                connected_devices=list(session.connected_devices)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session status: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get session status: {str(e)}"
            )
    
    @router.post("/api/remote/connect/{session_token}")
    async def connect_session(session_token: str):
        """
        Establish connection from mobile device.
        Returns connection confirmation (WebSocket upgrade happens separately).
        """
        try:
            session = remote_control_service.validate_remote_session(session_token)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found or expired"
                )
            
            # Add mobile device to session
            remote_control_service.remote_session_repository.add_connected_device(
                session.session_id,
                "mobile"
            )
            
            return {
                "success": True,
                "message": "Connection established",
                "session_id": session.session_id,
                "room_name": session.room_name
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error connecting to session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to session: {str(e)}"
            )
    
    @router.delete("/api/remote/session/{session_token}")
    async def delete_session(
        session_token: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """
        Terminate a remote session.
        Requires authentication or session token validation.
        """
        try:
            session = remote_control_service.validate_remote_session(session_token)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found or expired"
                )
            
            # Verify user owns the session
            if session.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to delete this session"
                )
            
            # Delete session
            remote_control_service.remote_session_repository.delete_session(session.session_id)
            
            return {
                "success": True,
                "message": "Session deleted successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete session: {str(e)}"
            )
    
    return router

