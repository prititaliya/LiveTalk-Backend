"""
Save Transcript Use Case

Use case for saving transcripts to repository.
Following Single Responsibility Principle - only handles transcript saving.
"""
from pathlib import Path
from application.services.transcript_service import TranscriptService
from domain.value_objects.meeting_id import MeetingId


class SaveTranscriptUseCase:
    """Use case for saving transcripts"""
    
    def __init__(self, transcript_service: TranscriptService):
        """
        Initialize use case.
        
        Args:
            transcript_service: Transcript service
        """
        self.transcript_service = transcript_service
    
    def execute(self, room_name: str, transcript_file_path: Path, user_id: str = None) -> MeetingId:
        """
        Execute transcript saving.
        
        Args:
            room_name: Name of the room
            transcript_file_path: Path to the transcript file
            
        Returns:
            MeetingId of the saved transcript
            
        Raises:
            ValueError: If transcript file cannot be read
            FileNotFoundError: If transcript file doesn't exist
        """
        if not transcript_file_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_file_path}")
        
        return self.transcript_service.save_transcript_to_repository(
            room_name=room_name,
            transcript_file_path=transcript_file_path,
            user_id=user_id
        )

