"""
Unified STT Service

Handles all STT providers (Speechmatics, Deepgram, AssemblyAI) in a single service.
Switching providers only requires changing STT_MODEL environment variable.
"""
import os
import inspect
import logging
from typing import Optional, Any
from domain.interfaces.stt_service import ISTTService

logger = logging.getLogger(__name__)

# Try importing all providers
try:
    from livekit.plugins import speechmatics
    SPEECHMATICS_AVAILABLE = True
except ImportError:
    SPEECHMATICS_AVAILABLE = False
    logger.warning("Speechmatics plugin not available")

try:
    from livekit.plugins import deepgram
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    logger.warning("Deepgram plugin not available")

try:
    from livekit.plugins import assemblyai
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    ASSEMBLYAI_AVAILABLE = False
    logger.warning("AssemblyAI plugin not available")


class UnifiedSTTService(ISTTService):
    """Unified STT service that handles all providers internally"""
    
    def __init__(self):
        """Initialize unified STT service"""
        self._model = os.environ.get("STT_MODEL", "speechmatics").lower()
        logger.info(f"Initialized UnifiedSTTService with model: {self._model}")
    
    def create_stt_engine(
        self,
        api_key: str = None,
        language: str = "en",
        enable_diarization: bool = True,
        **kwargs
    ) -> Any:
        """
        Create a speech-to-text engine instance based on STT_MODEL environment variable.
        
        Args:
            api_key: API key (if None, will be read from environment based on model)
            language: Language code (default: "en")
            enable_diarization: Whether to enable speaker diarization
            **kwargs: Additional configuration options
            
        Returns:
            STT engine instance
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = self._get_api_key()
        
        # Route to appropriate provider
        # For models without native diarization, don't pass enable_diarization
        if self._model == "speechmatics":
            return self._create_speechmatics_engine(api_key, language, enable_diarization, **kwargs)
        elif self._model == "deepgram":
            # Deepgram doesn't support native diarization - handled manually
            return self._create_deepgram_engine(api_key, language, False, **kwargs)
        elif self._model == "assemblyai":
            # AssemblyAI diarization handled manually
            return self._create_assemblyai_engine(api_key, language, False, **kwargs)
        else:
            raise ValueError(
                f"Invalid STT_MODEL: {self._model}. "
                f"Supported values: speechmatics, deepgram, assemblyai"
            )
    
    def _get_api_key(self) -> str:
        """Get API key from environment based on current model"""
        if self._model == "speechmatics":
            api_key = os.environ.get("SPEECHMATICS_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "SPEECHMATICS_API_KEY is required in environment. "
                    "Set STT_MODEL=speechmatics and provide SPEECHMATICS_API_KEY"
                )
            return api_key
        elif self._model == "deepgram":
            api_key = os.environ.get("DEEPGRAM_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "DEEPGRAM_API_KEY is required in environment. "
                    "Set STT_MODEL=deepgram and provide DEEPGRAM_API_KEY"
                )
            return api_key
        elif self._model == "assemblyai":
            api_key = os.environ.get("ASSEMBLYAI_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "ASSEMBLYAI_API_KEY is required in environment. "
                    "Set STT_MODEL=assemblyai and provide ASSEMBLYAI_API_KEY"
                )
            return api_key
        else:
            raise ValueError(f"Invalid STT_MODEL: {self._model}")
    
    def _create_speechmatics_engine(
        self,
        api_key: str,
        language: str,
        enable_diarization: bool,
        **kwargs
    ) -> Any:
        """Create Speechmatics STT engine"""
        if not SPEECHMATICS_AVAILABLE:
            raise RuntimeError(
                "Speechmatics plugin not available. "
                "Install with: pip install livekit-plugins-speechmatics"
            )
        
        stt_kwargs = {
            "api_key": api_key,
            "language": language,
            "enable_diarization": enable_diarization,
        }
        
        # Try adding max_speakers parameter if available (helps Speechmatics diarization accuracy)
        max_speakers = kwargs.get("max_speakers", 10)
        try:
            sig = inspect.signature(speechmatics.STT.__init__)
            if "max_speakers" in sig.parameters:
                stt_kwargs["max_speakers"] = max_speakers
                logger.info(f"✅ Using max_speakers={max_speakers} parameter for Speechmatics diarization")
            else:
                # Try alternative parameter names
                if "speaker_diarization_max_speakers" in sig.parameters:
                    stt_kwargs["speaker_diarization_max_speakers"] = max_speakers
                    logger.info(f"✅ Using speaker_diarization_max_speakers={max_speakers} for Speechmatics")
        except Exception as e:
            logger.debug(f"Could not set max_speakers parameter: {e}")
        
        # Add any additional kwargs (but don't override critical settings)
        for k, v in kwargs.items():
            if k not in stt_kwargs:
                stt_kwargs[k] = v
        
        logger.info(f"🎙️ Creating Speechmatics STT engine with diarization={enable_diarization}, max_speakers={max_speakers}")
        stt_engine = speechmatics.STT(**stt_kwargs)
        logger.info(f"✅ Speechmatics STT engine created successfully with native diarization")
        return stt_engine
    
    def _create_deepgram_engine(
        self,
        api_key: str,
        language: str,
        enable_diarization: bool,
        **kwargs
    ) -> Any:
        """Create Deepgram STT engine"""
        if not DEEPGRAM_AVAILABLE:
            raise RuntimeError(
                "Deepgram plugin not available. "
                "Install with: pip install livekit-plugins-deepgram"
            )
        
        stt_kwargs = {
            "api_key": api_key,
            "language": language,
        }
        
        # Deepgram doesn't support native diarization via parameters
        # Diarization will be handled manually in the speaker_diarization_service
        # Don't pass any diarization parameters to avoid errors
        
        # Add any additional kwargs (but filter out diarization-related ones)
        filtered_kwargs = {k: v for k, v in kwargs.items() if not k.startswith('diarize')}
        stt_kwargs.update(filtered_kwargs)
        
        logger.info(f"Creating Deepgram STT engine (diarization will be handled manually)")
        return deepgram.STT(**stt_kwargs)
    
    def _create_assemblyai_engine(
        self,
        api_key: str,
        language: str,
        enable_diarization: bool,
        **kwargs
    ) -> Any:
        """Create AssemblyAI STT engine"""
        if not ASSEMBLYAI_AVAILABLE:
            raise RuntimeError(
                "AssemblyAI plugin not available. "
                "Install with: pip install livekit-plugins-assemblyai or livekit-agents[assemblyai]"
            )
        
        stt_kwargs = {
            "api_key": api_key,
            "language": language,
        }
        
        # AssemblyAI uses 'speaker_labels' parameter instead of 'enable_diarization'
        if enable_diarization:
            stt_kwargs["speaker_labels"] = True
        
        # Add any additional kwargs
        stt_kwargs.update(kwargs)
        
        logger.info(f"Creating AssemblyAI STT engine with diarization: {enable_diarization}")
        return assemblyai.STT(**stt_kwargs)
    
    def is_diarization_supported(self) -> bool:
        """Check if speaker diarization is supported for current model"""
        return True  # All supported providers support diarization
    
    def get_max_speakers_limit(self) -> Optional[int]:
        """Get the maximum number of speakers supported for current model"""
        if self._model == "speechmatics":
            return 10  # Speechmatics typically supports up to 10 speakers
        elif self._model == "deepgram":
            return None  # Deepgram doesn't have a hard limit
        elif self._model == "assemblyai":
            return None  # AssemblyAI doesn't have a hard limit
        return None

