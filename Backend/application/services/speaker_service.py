"""
Speaker Service

Handles speaker labeling and identification logic.
Following Single Responsibility Principle - only handles speaker-related operations.
"""
from typing import Dict, Optional


class SpeakerService:
    """Service for managing speaker labels and identification"""
    
    def __init__(self):
        """Initialize speaker service with empty label map"""
        self.speaker_label_map: Dict[str, str] = {}
        self.next_speaker_num: int = 1
    
    def get_label_for_speaker_id(self, speaker_id: Optional[str]) -> str:
        """
        Generate or retrieve a label for a speaker ID.
        
        Args:
            speaker_id: The speaker ID (can be None)
            
        Returns:
            Human-readable speaker label (e.g., "Speaker 1")
        """
        if not speaker_id:
            speaker_id = "unknown"
        
        if speaker_id not in self.speaker_label_map:
            self.speaker_label_map[speaker_id] = f"Speaker {self.next_speaker_num}"
            self.next_speaker_num += 1
        
        return self.speaker_label_map[speaker_id]
    
    def reset(self):
        """Reset speaker labels for a new session"""
        self.speaker_label_map = {}
        self.next_speaker_num = 1
    
    def get_speaker_count(self) -> int:
        """Get the number of unique speakers"""
        return len(self.speaker_label_map)

