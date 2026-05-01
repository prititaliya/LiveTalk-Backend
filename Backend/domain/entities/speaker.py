"""
Speaker Entity

Represents a speaker in a meeting with their label and ID.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Speaker:
    """A speaker in a meeting"""
    speaker_id: str
    label: str
    
    def __post_init__(self):
        """Validate speaker data"""
        if not self.speaker_id:
            raise ValueError("Speaker ID cannot be empty")
        if not self.label:
            raise ValueError("Speaker label cannot be empty")
    
    def __eq__(self, other):
        """Two speakers are equal if they have the same ID"""
        if not isinstance(other, Speaker):
            return False
        return self.speaker_id == other.speaker_id
    
    def __hash__(self):
        """Hash based on speaker ID"""
        return hash(self.speaker_id)

