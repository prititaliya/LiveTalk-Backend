"""
Transcript Service

Handles transcript-related business logic.
Following Single Responsibility Principle - only handles transcript operations.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from domain.entities.meeting import Meeting
from domain.entities.transcript import Transcript
from domain.value_objects.meeting_id import MeetingId
from domain.interfaces.file_storage import IFileStorage
from data_access.repositories.transcript_repository import TranscriptRepository
from data_access.mappers.transcript_mapper import TranscriptMapper


class TranscriptService:
    """Service for managing transcripts"""
    
    def __init__(
        self,
        transcript_repository: TranscriptRepository,
        file_storage: IFileStorage
    ):
        """
        Initialize transcript service.
        
        Args:
            transcript_repository: Repository for transcript persistence
            file_storage: File storage for transcript files
        """
        self.transcript_repository = transcript_repository
        self.file_storage = file_storage
        self.mapper = TranscriptMapper()
    
    def create_transcript_file(
        self,
        room_name: str,
        transcripts_dir: Path
    ) -> Path:
        """
        Create a new transcript file for a room.
        
        Args:
            room_name: Name of the room
            transcripts_dir: Directory for transcript files
            
        Returns:
            Path to the created file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c for c in room_name if c.isalnum() or c in ("-", "_", " ")
        ).strip().replace(" ", "_")
        filename = f"{safe_name}_{timestamp}.json"
        file_path = transcripts_dir / filename
        
        initial_data = {
            "meeting_name": room_name,
            "start_time": datetime.now().isoformat(),
            "transcripts": []
        }
        
        self.file_storage.create_file(file_path, initial_data)
        return file_path
    
    def append_transcript_to_file(
        self,
        file_path: Path,
        speaker: str,
        text: str,
        timestamp: datetime
    ) -> bool:
        """
        Append a transcript entry to a file.
        
        Args:
            file_path: Path to the transcript file
            speaker: Speaker label
            text: Transcript text
            timestamp: Timestamp of the transcript
            
        Returns:
            True if successful, False otherwise
        """
        try:
            transcript_entry = {
                "speaker": speaker,
                "text": text,
                "timestamp": timestamp.isoformat(),
                "is_final": True
            }
            
            self.file_storage.append_to_file(file_path, {"transcripts": [transcript_entry]})
            return True
        except Exception as e:
            logger.error(f"Failed to append to transcript file: {e}")
            return False
    
    def save_transcript_to_repository(
        self,
        room_name: str,
        transcript_file_path: Path,
        user_id: Optional[str] = None
    ) -> MeetingId:
        """
        Save transcript from file to repository (Redis).
        
        Args:
            room_name: Name of the room
            transcript_file_path: Path to the transcript file
            
        Returns:
            MeetingId of the saved meeting
        """
        # Read file data
        file_data = self.file_storage.read_file(transcript_file_path)
        if not file_data:
            raise ValueError(f"Could not read transcript file: {transcript_file_path}")
        
        # Parse start_time for meeting ID generation
        start_time_str = file_data.get("start_time", datetime.now().isoformat())
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except:
            start_time = datetime.now()
        
        # Generate meeting ID first
        meeting_id = MeetingId.generate(room_name, start_time)
        
        # Convert to meeting entity with generated meeting_id
        meeting = self.mapper.dict_to_meeting({
            "meeting_id": meeting_id.value,
            "meeting_name": file_data.get("meeting_name", room_name),
            "room_name": room_name,
            "start_time": start_time_str,
            "transcripts": file_data.get("transcripts", []),
            "end_time": file_data.get("last_updated"),
            "created_at": file_data.get("start_time"),
        })
        
        # Add user_id if provided
        if user_id:
            meeting.user_id = user_id
        
        # Save to repository
        return self.transcript_repository.save(meeting)
    
    def get_transcript_by_id(self, meeting_id: MeetingId) -> Optional[Meeting]:
        """Get a transcript by meeting ID"""
        return self.transcript_repository.get_by_id(meeting_id)
    
    def search_transcripts(
        self,
        meeting_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Meeting]:
        """Search for transcripts"""
        return self.transcript_repository.search(
            meeting_name=meeting_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

