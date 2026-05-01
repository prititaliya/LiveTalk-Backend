"""
Transcript Repository

High-level repository that uses infrastructure repositories.
This provides a clean interface for the application layer.
"""
from typing import List, Optional
from datetime import datetime

from domain.interfaces.transcript_repository import ITranscriptRepository
from domain.entities.meeting import Meeting
from domain.value_objects.meeting_id import MeetingId
from infrastructure.repositories.redis_transcript_repository import RedisTranscriptRepository


class TranscriptRepository:
    """
    Transcript repository that delegates to infrastructure implementation.
    
    This follows the Repository pattern and allows swapping implementations
    without changing application layer code.
    """
    
    def __init__(self, repository: Optional[ITranscriptRepository] = None):
        """
        Initialize repository with optional infrastructure implementation.
        
        Args:
            repository: Infrastructure repository implementation (defaults to Redis)
        """
        self._repository = repository or RedisTranscriptRepository()
    
    def save(self, meeting: Meeting) -> MeetingId:
        """Save a meeting with its transcripts"""
        return self._repository.save(meeting)
    
    def get_by_id(self, meeting_id: MeetingId) -> Optional[Meeting]:
        """Retrieve a meeting by its ID"""
        return self._repository.get_by_id(meeting_id)
    
    def search(
        self,
        meeting_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Meeting]:
        """Search for meetings by various criteria"""
        return self._repository.search(
            meeting_name=meeting_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
    
    def delete(self, meeting_id: MeetingId) -> bool:
        """Delete a meeting by its ID"""
        return self._repository.delete(meeting_id)

