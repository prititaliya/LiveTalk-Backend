"""
Speaker Diarization Service

Handles speaker change detection and diarization logic.
Automatically determines whether to use native or manual diarization based on STT model.
Following Single Responsibility Principle - only handles diarization.
"""
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SpeakerDiarizationService:
    """Service for speaker diarization and change detection"""
    
    def __init__(self, history_size: int = 20):
        """
        Initialize diarization service.
        
        Args:
            history_size: Number of recent speaker IDs to track
        """
        self.recent_speaker_ids: List[str] = []
        self.last_speaker_id: Optional[str] = None
        self.history_size = history_size
        self._stt_model = os.environ.get("STT_MODEL", "speechmatics").lower()
        logger.info(f"SpeakerDiarizationService initialized for STT model: {self._stt_model}")
    
    def has_native_diarization(self) -> bool:
        """
        Check if the current STT model has native diarization support.
        
        Returns:
            True if model supports native diarization, False if manual processing needed
        """
        # Speechmatics has native diarization support
        if self._stt_model == "speechmatics":
            return True
        # Deepgram and AssemblyAI need manual diarization
        return False
    
    def get_stt_diarization_config(self) -> dict:
        """
        Get STT engine configuration for diarization.
        Returns appropriate parameters based on whether model has native support.
        
        Returns:
            Dictionary of configuration parameters for STT engine
        """
        if self._stt_model == "speechmatics":
            return {
                "enable_diarization": True,
                "max_speakers": 10
            }
        elif self._stt_model == "deepgram":
            # Deepgram doesn't support native diarization
            # Return empty dict - diarization will be handled manually
            return {}
        elif self._stt_model == "assemblyai":
            # AssemblyAI may have speaker_labels, but we'll handle manually for consistency
            return {}
        else:
            # Default: no native support
            return {}
    
    def detect_speaker(
        self,
        speaker_id_attr: Optional[str],
        speaker_attr: Optional[str],
        speaker_label_attr: Optional[str],
        alt_dict: Optional[dict] = None
    ) -> str:
        """
        Detect speaker ID from various attributes.
        
        Args:
            speaker_id_attr: Speaker ID from alternative attribute
            speaker_attr: Speaker from alternative attribute
            speaker_label_attr: Speaker label from alternative attribute
            alt_dict: Dictionary representation of alternative
            
        Returns:
            Detected speaker ID
        """
        # Try multiple ways to get speaker information
        spk = speaker_id_attr or speaker_attr or speaker_label_attr
        
        if not spk and alt_dict:
            spk = alt_dict.get("speaker_id") or alt_dict.get("speaker") or alt_dict.get("speaker_label")
        
        # Fallback to speaker_1 if nothing found
        if not spk:
            spk = "speaker_1"
        
        return spk
    
    def track_speaker_change(self, current_speaker_id: str) -> str:
        """
        Track speaker changes and detect if a different speaker should be used.
        
        Args:
            current_speaker_id: The currently detected speaker ID
            
        Returns:
            Final speaker ID to use (may be different if change detected)
        """
        # Track recent speaker IDs
        self.recent_speaker_ids.append(current_speaker_id)
        if len(self.recent_speaker_ids) > self.history_size:
            self.recent_speaker_ids.pop(0)
        
        # Check for speaker changes
        unique_recent_speakers = list(set(self.recent_speaker_ids[-10:]))
        
        # If multiple speakers detected in recent history, prioritize the most recent one
        if len(unique_recent_speakers) > 1:
            # Count occurrences of each speaker in recent history
            speaker_counts = {}
            for s in self.recent_speaker_ids[-10:]:
                speaker_counts[s] = speaker_counts.get(s, 0) + 1
            
            # If current speaker is same as last, but another speaker appeared recently
            if self.last_speaker_id and current_speaker_id == self.last_speaker_id:
                # Check if there's a different speaker that appeared multiple times
                for recent_spk, count in speaker_counts.items():
                    if recent_spk != self.last_speaker_id and count >= 2:
                        # Another speaker appeared at least twice - likely a real change
                        current_speaker_id = recent_spk
                        break
        
        self.last_speaker_id = current_speaker_id
        return current_speaker_id
    
    def reset(self):
        """Reset diarization state for a new session"""
        self.recent_speaker_ids = []
        self.last_speaker_id = None

