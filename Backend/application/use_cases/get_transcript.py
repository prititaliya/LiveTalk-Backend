"""
Get Transcript Use Case

Use case for retrieving transcripts.
Following Single Responsibility Principle - only handles transcript retrieval.
"""
from typing import Optional
from domain.entities.meeting import Meeting
from domain.value_objects.meeting_id import MeetingId
from data_access.repositories.transcript_repository import TranscriptRepository


class GetTranscriptUseCase:
    """Use case for retrieving transcripts"""
    
    def __init__(self, transcript_repository: TranscriptRepository):
        """
        Initialize use case.
        
        Args:
            transcript_repository: Transcript repository
        """
        self.transcript_repository = transcript_repository
    
    def execute(self, meeting_id: MeetingId) -> Optional[Meeting]:
        """
        Execute transcript retrieval.
        
        Args:
            meeting_id: Meeting ID to retrieve
            
        Returns:
            Meeting entity if found, None otherwise
        """
        return self.transcript_repository.get_by_id(meeting_id)

