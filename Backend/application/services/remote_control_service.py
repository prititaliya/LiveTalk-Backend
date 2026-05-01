"""
Remote Control Service

Handles remote recording control session management and commands.
"""
import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from domain.entities.remote_session import RemoteSession
from domain.interfaces.remote_session_repository import IRemoteSessionRepository
from infrastructure.services.qr_code_service import QRCodeService
from infrastructure.services.livekit_service import LiveKitService
from application.services.jwt_service import JWTService
from application.services.recording_state_service import RecordingStateService
from core.config import get_config

logger = logging.getLogger(__name__)


class RemoteControlService:
    """Service for remote recording control"""
    
    def __init__(
        self,
        remote_session_repository: IRemoteSessionRepository,
        qr_code_service: QRCodeService,
        livekit_service: LiveKitService,
        jwt_service: JWTService,
        recording_state_service: RecordingStateService
    ):
        """
        Initialize remote control service.
        
        Args:
            remote_session_repository: Repository for remote session operations
            qr_code_service: Service for QR code generation
            livekit_service: Service for LiveKit operations
            jwt_service: Service for JWT token operations
            recording_state_service: Service for recording state management
        """
        self.remote_session_repository = remote_session_repository
        self.qr_code_service = qr_code_service
        self.livekit_service = livekit_service
        self.jwt_service = jwt_service
        self.recording_state_service = recording_state_service
        self.config = get_config()
        logger.info("RemoteControlService initialized")
    
    def generate_remote_session(self, user_id: str, room_name: str) -> Dict:
        """
        Generate a remote session with QR code.
        
        Args:
            user_id: User ID creating the session
            room_name: Name of the room for recording
            
        Returns:
            Dictionary with session_token, qr_code_data, expires_at, session_id
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Generate session token (JWT)
        expires_delta = timedelta(seconds=self.config.remote_session_expiry_seconds)
        session_token = self.jwt_service.create_access_token(
            data={
                "sub": user_id,
                "session_id": session_id,
                "room_name": room_name,
                "type": "remote_session"
            },
            expires_delta=expires_delta
        )
        
        # Calculate expiration time
        expires_at = datetime.now() + expires_delta
        
        # Create remote session entity
        session = RemoteSession(
            session_id=session_id,
            user_id=user_id,
            room_name=room_name,
            created_at=datetime.now(),
            expires_at=expires_at,
            status="pending",
            connected_devices=set(),
            recording_state="idle",
            session_token=session_token
        )
        
        # Save session to repository
        self.remote_session_repository.create_session(session)
        
        # Generate QR code
        # Use BASE_URL from environment, fallback to localhost
        # This should be set to your public-facing URL (e.g., ngrok URL)
        base_url = os.environ.get("BASE_URL", "http://localhost:3000")
        # Ensure base_url doesn't end with a slash
        base_url = base_url.rstrip("/")
        qr_data = f"{base_url}/remote/{session_token}"
        qr_code_data = self.qr_code_service.generate_qr_code(
            qr_data,
            size=self.config.remote_qr_code_size
        )
        
        logger.info(f"Generated remote session {session_id} for user {user_id}, room {room_name}")
        
        return {
            "session_token": session_token,
            "qr_code_data": qr_code_data,
            "expires_at": expires_at.isoformat(),
            "session_id": session_id
        }
    
    def validate_remote_session(self, token: str) -> Optional[RemoteSession]:
        """
        Validate a remote session token.
        
        Args:
            token: Session token to validate
            
        Returns:
            RemoteSession if valid, None otherwise
        """
        # Verify JWT token
        payload = self.jwt_service.verify_token(token)
        if not payload:
            logger.warning("Invalid JWT token")
            return None
        
        # Check token type
        if payload.get("type") != "remote_session":
            logger.warning("Token is not a remote session token")
            return None
        
        # Get session from repository
        session = self.remote_session_repository.get_session_by_token(token)
        if not session:
            logger.warning(f"Session not found for token")
            return None
        
        # Check expiration
        if session.is_expired():
            logger.warning(f"Session {session.session_id} has expired")
            self.remote_session_repository.update_session_status(session.session_id, "expired")
            return None
        
        # Check if can connect
        if not session.can_connect():
            logger.warning(f"Session {session.session_id} cannot accept connections")
            return None
        
        return session
    
    def handle_remote_command(
        self,
        session_id: str,
        command: str,
        source_device: str
    ) -> Dict:
        """
        Handle a remote command from mobile or laptop.
        
        Args:
            session_id: The session ID
            command: Command to execute (start_recording, stop_recording, pause_recording, resume_recording)
            source_device: Source device ('laptop' or 'mobile')
            
        Returns:
            Dictionary with success status, message, and new state
        """
        # Get session
        session = self.remote_session_repository.get_session(session_id)
        if not session:
            return {
                "success": False,
                "message": "Session not found",
                "state": "idle"
            }
        
        # Validate command
        valid_commands = ['start_recording', 'stop_recording', 'pause_recording', 'resume_recording', 'end_session']
        if command not in valid_commands:
            return {
                "success": False,
                "message": f"Invalid command: {command}",
                "state": session.recording_state
            }
        
        # Handle end_session command
        if command == "end_session":
            self.remote_session_repository.delete_session(session_id)
            return {
                "success": True,
                "message": "Session ended",
                "state": "stopped"
            }
        
        # Determine new state based on command
        current_state = session.recording_state
        new_state = current_state
        
        if command == "start_recording":
            if current_state == "idle" or current_state == "stopped":
                new_state = "recording"
            else:
                return {
                    "success": False,
                    "message": f"Cannot start recording from state: {current_state}",
                    "state": current_state
                }
        elif command == "stop_recording":
            if current_state in ["recording", "paused"]:
                new_state = "stopped"
            else:
                return {
                    "success": False,
                    "message": f"Cannot stop recording from state: {current_state}",
                    "state": current_state
                }
        elif command == "pause_recording":
            if current_state == "recording":
                new_state = "paused"
            else:
                return {
                    "success": False,
                    "message": f"Cannot pause recording from state: {current_state}",
                    "state": current_state
                }
        elif command == "resume_recording":
            if current_state == "paused":
                new_state = "recording"
            else:
                return {
                    "success": False,
                    "message": f"Cannot resume recording from state: {current_state}",
                    "state": current_state
                }
        
        # Update state
        success = self.remote_session_repository.update_recording_state(session_id, new_state)
        if success:
            # Also update recording state service
            self.recording_state_service.update_agent_state(session_id, new_state)
            
            # Try to find and call agent's stop_recording method directly
            # This ensures immediate response instead of waiting for polling
            if command == "stop_recording" and new_state == "stopped":
                try:
                    # Import here to avoid circular dependency
                    import sys
                    import importlib
                    # Try to import the main module dynamically
                    main_module = sys.modules.get('main')
                    if not main_module:
                        # Try importing it
                        import main
                        main_module = main
                    if main_module and hasattr(main_module, '_active_agents'):
                        _active_agents = main_module._active_agents
                        # Find agent by room_name from session
                        if session and session.room_name:
                            agent = _active_agents.get(session.room_name)
                            if agent:
                                logger.info(f"🎯 Directly calling stop_recording on agent for room: {session.room_name}")
                                agent.stop_recording()
                except Exception as e:
                    logger.debug(f"Could not directly call agent stop_recording: {e}")
                    # Fallback to Redis polling (already set above)
            
            logger.info(f"Command {command} executed for session {session_id} by {source_device}, state: {current_state} -> {new_state}")
            
            return {
                "success": True,
                "message": f"Command {command} executed successfully",
                "state": new_state
            }
        else:
            return {
                "success": False,
                "message": "Failed to update recording state",
                "state": current_state
            }
    
    def sync_recording_state(self, session_id: str, state: str) -> None:
        """
        Sync recording state and broadcast to connected devices.
        
        Args:
            session_id: The session ID
            state: New recording state
        """
        self.remote_session_repository.update_recording_state(session_id, state)
        self.recording_state_service.update_agent_state(session_id, state)
        logger.debug(f"Synced recording state for session {session_id}: {state}")
    
    def disconnect_remote_session(self, session_id: str, device: str) -> None:
        """
        Disconnect a device from remote session.
        
        Args:
            session_id: The session ID
            device: Device type ('laptop' or 'mobile')
        """
        self.remote_session_repository.remove_connected_device(session_id, device)
        logger.info(f"Device {device} disconnected from session {session_id}")
    
    def get_recording_state(self, session_id: str) -> Dict:
        """
        Get current recording state for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with recording state information
        """
        session = self.remote_session_repository.get_session(session_id)
        if not session:
            return {
                "state": "idle",
                "session_exists": False
            }
        
        return {
            "state": session.recording_state,
            "session_exists": True,
            "room_name": session.room_name,
            "status": session.status,
            "connected_devices": list(session.connected_devices)
        }

