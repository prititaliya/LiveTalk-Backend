"""
Generate Remote Session Use Case

Use case for generating remote recording control sessions.
"""
from typing import Dict
from application.services.remote_control_service import RemoteControlService


class GenerateRemoteSessionUseCase:
    """Use case for generating remote sessions"""
    
    def __init__(self, remote_control_service: RemoteControlService):
        """
        Initialize use case.
        
        Args:
            remote_control_service: Remote control service
        """
        self.remote_control_service = remote_control_service
    
    def execute(self, user_id: str, room_name: str) -> Dict:
        """
        Execute remote session generation.
        
        Args:
            user_id: User ID creating the session
            room_name: Name of the room for recording
            
        Returns:
            Dictionary with session_token, qr_code_data, expires_at, session_id
        """
        return self.remote_control_service.generate_remote_session(user_id, room_name)

