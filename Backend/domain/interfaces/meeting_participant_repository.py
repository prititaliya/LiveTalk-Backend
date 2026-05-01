"""
Meeting Participant Repository Interface

Defines the contract for meeting participant data persistence.
Following Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

from ..entities.meeting_participant import MeetingParticipant


class IMeetingParticipantRepository(ABC):
    """Interface for meeting participant repository operations"""
    
    @abstractmethod
    def add(self, participant: MeetingParticipant) -> MeetingParticipant:
        """
        Add a participant to a meeting.
        
        Args:
            participant: The participant entity to add
            
        Returns:
            Added MeetingParticipant entity
            
        Raises:
            ValueError: If participant already exists
        """
        pass
    
    @abstractmethod
    def remove(self, meeting_id: str, user_id: str) -> bool:
        """
        Remove a participant from a meeting.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID to remove
            
        Returns:
            True if removed, False if not found
        """
        pass
    
    @abstractmethod
    def find_by_meeting(self, meeting_id: str) -> List[MeetingParticipant]:
        """
        Find all participants for a meeting.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            List of MeetingParticipant entities
        """
        pass
    
    @abstractmethod
    def find_by_user_and_meeting(self, meeting_id: str, user_id: str) -> Optional[MeetingParticipant]:
        """
        Find a specific participant by meeting and user ID.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID
            
        Returns:
            MeetingParticipant entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_permissions(self, meeting_id: str, user_id: str, permissions: Dict[str, bool]) -> Optional[MeetingParticipant]:
        """
        Update participant permissions.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID
            permissions: Dictionary of permission updates
            
        Returns:
            Updated MeetingParticipant entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_role(self, meeting_id: str, user_id: str, role: str) -> Optional[MeetingParticipant]:
        """
        Update participant role.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID
            role: New role ("viewer" or "collaborator")
            
        Returns:
            Updated MeetingParticipant entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_last_accessed(self, meeting_id: str, user_id: str) -> bool:
        """
        Update the last accessed timestamp for a participant.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user ID
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    def count_by_meeting(self, meeting_id: str) -> int:
        """
        Count the number of participants for a meeting.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            Number of participants
        """
        pass

