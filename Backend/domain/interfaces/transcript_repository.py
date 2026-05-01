"""
Transcript Repository Interface

Defines the contract for transcript data persistence.
Following Dependency Inversion Principle - high-level modules depend on this abstraction.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.meeting import Meeting
from ..value_objects.meeting_id import MeetingId


class ITranscriptRepository(ABC):
    """Interface for transcript repository operations"""
    
    @abstractmethod
    def save(self, meeting: Meeting) -> MeetingId:
        """
        Save a meeting with its transcripts.
        
        Args:
            meeting: The meeting entity to save
            
        Returns:
            MeetingId of the saved meeting
        """
        pass
    
    @abstractmethod
    def get_by_id(self, meeting_id: MeetingId) -> Optional[Meeting]:
        """
        Retrieve a meeting by its ID.
        
        Args:
            meeting_id: The meeting ID to retrieve
            
        Returns:
            Meeting entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def search(
        self,
        meeting_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Meeting]:
        """
        Search for meetings by various criteria.
        
        Args:
            meeting_name: Filter by meeting name (partial match)
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum number of results
            
        Returns:
            List of matching Meeting entities
        """
        pass
    
    @abstractmethod
    def delete(self, meeting_id: MeetingId) -> bool:
        """
        Delete a meeting by its ID.
        
        Args:
            meeting_id: The meeting ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass

