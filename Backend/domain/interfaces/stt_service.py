"""
Speech-to-Text Service Interface

Defines the contract for STT operations.
Following Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ISTTService(ABC):
    """Interface for Speech-to-Text service operations"""
    
    @abstractmethod
    def create_stt_engine(
        self,
        api_key: str,
        language: str = "en",
        enable_diarization: bool = True,
        **kwargs
    ) -> Any:
        """
        Create a speech-to-text engine instance.
        
        Args:
            api_key: API key for the STT service
            language: Language code (default: "en")
            enable_diarization: Whether to enable speaker diarization
            **kwargs: Additional configuration options
            
        Returns:
            STT engine instance (implementation-specific)
        """
        pass
    
    @abstractmethod
    def is_diarization_supported(self) -> bool:
        """
        Check if speaker diarization is supported.
        
        Returns:
            True if diarization is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_max_speakers_limit(self) -> Optional[int]:
        """
        Get the maximum number of speakers supported.
        
        Returns:
            Maximum speakers or None if unlimited
        """
        pass

