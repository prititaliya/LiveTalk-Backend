"""
LiveKit Service Interface

Defines the contract for LiveKit operations.
Following Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Optional


class ILiveKitService(ABC):
    """Interface for LiveKit service operations"""
    
    @abstractmethod
    def generate_access_token(
        self,
        participant_name: str,
        room_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True
    ) -> str:
        """
        Generate a LiveKit access token for a participant.
        
        Args:
            participant_name: Name of the participant
            room_name: Name of the room to join
            can_publish: Whether participant can publish tracks
            can_subscribe: Whether participant can subscribe to tracks
            
        Returns:
            JWT token string
        """
        pass
    
    @abstractmethod
    def get_server_url(self) -> str:
        """
        Get the LiveKit server URL.
        
        Returns:
            Server URL (e.g., "ws://localhost:7880")
        """
        pass

