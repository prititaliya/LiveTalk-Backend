"""
Transcript Entity

Represents a single transcript entry with speaker, text, and timestamp.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Transcript:
    """A single transcript entry"""
    speaker: str
    text: str
    timestamp: datetime
    is_final: bool = True
    
    def __post_init__(self):
        """Validate transcript data"""
        if not self.speaker:
            raise ValueError("Speaker cannot be empty")
        if not self.text:
            raise ValueError("Text cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")

