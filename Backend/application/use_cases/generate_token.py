"""
Generate Token Use Case

Use case for generating LiveKit access tokens.
Following Single Responsibility Principle - only handles token generation.
"""
from domain.interfaces.livekit_service import ILiveKitService


class GenerateTokenUseCase:
    """Use case for generating LiveKit access tokens"""
    
    def __init__(self, livekit_service: ILiveKitService):
        """
        Initialize use case.
        
        Args:
            livekit_service: LiveKit service implementation
        """
        self.livekit_service = livekit_service
    
    def execute(
        self,
        participant_name: str,
        room_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True
    ) -> dict:
        """
        Execute token generation.
        
        Args:
            participant_name: Name of the participant
            room_name: Name of the room
            can_publish: Whether participant can publish
            can_subscribe: Whether participant can subscribe
            
        Returns:
            Dictionary with token and URL
        """
        token = self.livekit_service.generate_access_token(
            participant_name=participant_name,
            room_name=room_name,
            can_publish=can_publish,
            can_subscribe=can_subscribe
        )
        
        url = self.livekit_service.get_server_url()
        
        return {
            "token": token,
            "url": url
        }

