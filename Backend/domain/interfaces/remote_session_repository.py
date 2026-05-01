"""
Remote Session Repository Interface

Interface for remote session repository operations.
"""
from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.remote_session import RemoteSession


class IRemoteSessionRepository(ABC):
    """Interface for remote session repository"""
    
    @abstractmethod
    def create_session(self, session: RemoteSession) -> str:
        """
        Create a new remote session.
        
        Args:
            session: RemoteSession entity to create
            
        Returns:
            Session ID of the created session
        """
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[RemoteSession]:
        """
        Get a remote session by session ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            RemoteSession if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_session_by_token(self, token: str) -> Optional[RemoteSession]:
        """
        Get a remote session by session token.
        
        Args:
            token: The session token
            
        Returns:
            RemoteSession if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_session_status(self, session_id: str, status: str) -> bool:
        """
        Update the status of a remote session.
        
        Args:
            session_id: The session ID
            status: New status ('pending', 'active', 'expired')
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update_recording_state(self, session_id: str, state: str) -> bool:
        """
        Update the recording state of a remote session.
        
        Args:
            session_id: The session ID
            state: New recording state ('idle', 'recording', 'paused', 'stopped')
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_connected_device(self, session_id: str, device: str) -> bool:
        """
        Add a connected device to the session.
        
        Args:
            session_id: The session ID
            device: Device type ('laptop' or 'mobile')
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_connected_device(self, session_id: str, device: str) -> bool:
        """
        Remove a connected device from the session.
        
        Args:
            session_id: The session ID
            device: Device type ('laptop' or 'mobile')
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a remote session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass

