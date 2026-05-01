"""
Meeting Entity

Represents a meeting/recording session with transcripts.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .transcript import Transcript


@dataclass
class Meeting:
    """A meeting/recording session"""
    meeting_id: str
    meeting_name: str
    room_name: str
    start_time: datetime
    transcripts: List[Transcript] = field(default_factory=list)
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate meeting data"""
        if not self.meeting_id:
            raise ValueError("Meeting ID cannot be empty")
        if not self.meeting_name:
            raise ValueError("Meeting name cannot be empty")
        if not self.room_name:
            raise ValueError("Room name cannot be empty")
        if not isinstance(self.start_time, datetime):
            raise ValueError("Start time must be a datetime object")
        
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def total_entries(self) -> int:
        """Get total number of transcript entries"""
        return len(self.transcripts)
    
    def add_transcript(self, transcript: Transcript) -> None:
        """Add a transcript entry to the meeting"""
        if not isinstance(transcript, Transcript):
            raise ValueError("Transcript must be a Transcript entity")
        self.transcripts.append(transcript)
        self.end_time = datetime.now()
    
    def get_transcripts_by_speaker(self, speaker: str) -> List[Transcript]:
        """Get all transcripts for a specific speaker"""
        return [t for t in self.transcripts if t.speaker == speaker]

