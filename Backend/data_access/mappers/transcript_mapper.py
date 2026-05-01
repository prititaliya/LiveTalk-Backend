"""
Transcript Mapper

Maps between domain entities and data transfer objects (DTOs).
"""
from typing import Dict, List
from datetime import datetime

from domain.entities.meeting import Meeting
from domain.entities.transcript import Transcript
from domain.value_objects.meeting_id import MeetingId


class TranscriptMapper:
    """Mapper for transcript-related conversions"""
    
    @staticmethod
    def meeting_to_dict(meeting: Meeting) -> Dict:
        """
        Convert Meeting entity to dictionary (for JSON serialization).
        
        Args:
            meeting: Meeting entity
            
        Returns:
            Dictionary representation
        """
        return {
            "meeting_id": meeting.meeting_id,
            "meeting_name": meeting.meeting_name,
            "room_name": meeting.room_name,
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
            "transcripts": [
                {
                    "speaker": t.speaker,
                    "text": t.text,
                    "timestamp": t.timestamp.isoformat(),
                    "is_final": t.is_final
                }
                for t in meeting.transcripts
            ],
            "total_entries": meeting.total_entries,
            "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
            "user_id": meeting.user_id,  # Optional user_id
        }
    
    @staticmethod
    def dict_to_meeting(data: Dict) -> Meeting:
        """
        Convert dictionary to Meeting entity.
        
        Args:
            data: Dictionary with meeting data
            
        Returns:
            Meeting entity
        """
        # Parse transcripts
        transcripts = [
            Transcript(
                speaker=t["speaker"],
                text=t["text"],
                timestamp=datetime.fromisoformat(t["timestamp"]),
                is_final=t.get("is_final", True)
            )
            for t in data.get("transcripts", [])
        ]
        
        # Create meeting
        return Meeting(
            meeting_id=data["meeting_id"],
            meeting_name=data["meeting_name"],
            room_name=data["room_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            transcripts=transcripts,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            user_id=data.get("user_id"),  # Optional user_id
        )
    
    @staticmethod
    def transcript_to_dict(transcript: Transcript) -> Dict:
        """
        Convert Transcript entity to dictionary.
        
        Args:
            transcript: Transcript entity
            
        Returns:
            Dictionary representation
        """
        return {
            "speaker": transcript.speaker,
            "text": transcript.text,
            "timestamp": transcript.timestamp.isoformat(),
            "is_final": transcript.is_final
        }
    
    @staticmethod
    def dict_to_transcript(data: Dict) -> Transcript:
        """
        Convert dictionary to Transcript entity.
        
        Args:
            data: Dictionary with transcript data
            
        Returns:
            Transcript entity
        """
        return Transcript(
            speaker=data["speaker"],
            text=data["text"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            is_final=data.get("is_final", True)
        )

