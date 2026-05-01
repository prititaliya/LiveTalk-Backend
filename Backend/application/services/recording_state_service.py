"""
Recording State Service

Manages recording state across agent and remote control.
"""
import logging
from typing import Optional, Dict
from domain.interfaces.remote_session_repository import IRemoteSessionRepository

logger = logging.getLogger(__name__)


class RecordingStateService:
    """Service for managing recording state"""
    
    def __init__(self, remote_session_repository: IRemoteSessionRepository):
        """
        Initialize recording state service.
        
        Args:
            remote_session_repository: Repository for remote session operations
        """
        self.remote_session_repository = remote_session_repository
        logger.info("RecordingStateService initialized")
    
    def update_agent_state(self, session_id: str, state: str) -> bool:
        """
        Update agent recording state.
        
        Args:
            session_id: The session ID
            state: New recording state ('idle', 'recording', 'paused', 'stopped')
            
        Returns:
            True if update was successful, False otherwise
        """
        if state not in ['idle', 'recording', 'paused', 'stopped']:
            logger.error(f"Invalid recording state: {state}")
            return False
        
        success = self.remote_session_repository.update_recording_state(session_id, state)
        if success:
            logger.info(f"Updated agent state for session {session_id} to {state}")
        else:
            logger.warning(f"Failed to update agent state for session {session_id}")
        
        return success
    
    def get_agent_state(self, session_id: str) -> Optional[str]:
        """
        Get current agent recording state.
        
        Args:
            session_id: The session ID
            
        Returns:
            Current recording state or None if session not found
        """
        session = self.remote_session_repository.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        return session.recording_state
    
    def notify_state_change(self, session_id: str, state: str, source: str) -> None:
        """
        Broadcast state changes (to be used by WebSocket manager).
        
        Args:
            session_id: The session ID
            state: New recording state
            source: Source of the change ('laptop' or 'mobile')
        """
        logger.info(f"State change notification: session={session_id}, state={state}, source={source}")
        # This method is a placeholder for WebSocket broadcasting
        # The actual broadcasting will be handled by the WebSocket manager
        # that calls this service

