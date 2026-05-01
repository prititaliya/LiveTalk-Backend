"""
Dependency Injection Container

Simple dependency injection container for managing dependencies.
Following Dependency Inversion Principle.
"""
from pathlib import Path

from infrastructure.config.redis_config import get_redis_client
from infrastructure.storage.file_storage import FileStorage
from infrastructure.services.livekit_service import LiveKitService
from infrastructure.services.unified_stt_service import UnifiedSTTService
from infrastructure.services.qr_code_service import QRCodeService
from infrastructure.repositories.redis_transcript_repository import RedisTranscriptRepository
from infrastructure.repositories.redis_remote_session_repository import RedisRemoteSessionRepository
from infrastructure.database.database import get_db, SessionLocal
from data_access.repositories.transcript_repository import TranscriptRepository
from data_access.repositories.user_repository import UserRepository
from application.services.transcript_service import TranscriptService
from application.services.speaker_service import SpeakerService
from application.services.speaker_diarization_service import SpeakerDiarizationService
from application.services.auth_service import AuthService
from application.services.jwt_service import JWTService
from application.services.remote_control_service import RemoteControlService
from application.services.recording_state_service import RecordingStateService
from application.use_cases.generate_token import GenerateTokenUseCase
from application.use_cases.save_transcript import SaveTranscriptUseCase
from application.use_cases.generate_remote_session import GenerateRemoteSessionUseCase
from application.use_cases.register_user import RegisterUserUseCase
from application.use_cases.login_user import LoginUserUseCase
from application.services.otp_service import OTPService
from infrastructure.services.email_service import EmailService
from core.config import get_config


class DIContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        """Initialize container and setup dependencies"""
        config = get_config()
        
        # Infrastructure
        self._file_storage = FileStorage(config.transcripts_dir)
        self._livekit_service = LiveKitService()
        self._stt_service = UnifiedSTTService()
        self._redis_repository = RedisTranscriptRepository()
        self._qr_code_service = QRCodeService(default_size=config.remote_qr_code_size)
        self._remote_session_repository = RedisRemoteSessionRepository()
        
        # Database session factory (will be used per request)
        self._db_session_factory = SessionLocal
        
        # Data Access
        self._transcript_repository = TranscriptRepository(self._redis_repository)
        
        # Application Services
        self._transcript_service = TranscriptService(
            self._transcript_repository,
            self._file_storage
        )
        self._speaker_service = SpeakerService()
        self._diarization_service = SpeakerDiarizationService()
        self._jwt_service = JWTService()
        self._recording_state_service = RecordingStateService(self._remote_session_repository)
        self._remote_control_service = RemoteControlService(
            remote_session_repository=self._remote_session_repository,
            qr_code_service=self._qr_code_service,
            livekit_service=self._livekit_service,
            jwt_service=self._jwt_service,
            recording_state_service=self._recording_state_service
        )
        
        # Email and OTP services (singletons)
        self._email_service = EmailService()
        self._otp_service = OTPService()
        
        # Use Cases
        self._generate_token_use_case = GenerateTokenUseCase(self._livekit_service)
        self._save_transcript_use_case = SaveTranscriptUseCase(self._transcript_service)
        self._generate_remote_session_use_case = GenerateRemoteSessionUseCase(self._remote_control_service)
    
    def file_storage(self) -> FileStorage:
        """Get file storage instance"""
        return self._file_storage
    
    def generate_token_use_case(self) -> GenerateTokenUseCase:
        """Get generate token use case"""
        return self._generate_token_use_case
    
    def save_transcript_use_case(self) -> SaveTranscriptUseCase:
        """Get save transcript use case"""
        return self._save_transcript_use_case
    
    def transcript_service(self) -> TranscriptService:
        """Get transcript service"""
        return self._transcript_service
    
    def speaker_service(self) -> SpeakerService:
        """Get speaker service"""
        return self._speaker_service
    
    def speaker_diarization_service(self) -> SpeakerDiarizationService:
        """Get speaker diarization service"""
        return self._diarization_service
    
    def stt_service(self) -> UnifiedSTTService:
        """Get STT service"""
        return self._stt_service
    
    def livekit_service(self) -> LiveKitService:
        """Get LiveKit service"""
        return self._livekit_service
    
    def db_session_factory(self):
        """Get database session factory"""
        return self._db_session_factory
    
    def jwt_service(self) -> JWTService:
        """Get JWT service"""
        return self._jwt_service
    
    def auth_service(self, db_session) -> AuthService:
        """
        Get auth service with database session.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            AuthService instance
        """
        user_repository = UserRepository(db_session)
        return AuthService(user_repository)
    
    def register_user_use_case(self, db_session) -> RegisterUserUseCase:
        """
        Get register user use case with database session.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            RegisterUserUseCase instance
        """
        auth_service = self.auth_service(db_session)
        return RegisterUserUseCase(auth_service)
    
    def login_user_use_case(self, db_session) -> LoginUserUseCase:
        """
        Get login user use case with database session.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            LoginUserUseCase instance
        """
        auth_service = self.auth_service(db_session)
        return LoginUserUseCase(auth_service, self._jwt_service)
    
    def qr_code_service(self) -> QRCodeService:
        """Get QR code service"""
        return self._qr_code_service
    
    def remote_session_repository(self) -> RedisRemoteSessionRepository:
        """Get remote session repository"""
        return self._remote_session_repository
    
    def remote_control_service(self) -> RemoteControlService:
        """Get remote control service"""
        return self._remote_control_service
    
    def recording_state_service(self) -> RecordingStateService:
        """Get recording state service"""
        return self._recording_state_service
    
    def generate_remote_session_use_case(self) -> GenerateRemoteSessionUseCase:
        """Get generate remote session use case"""
        return self._generate_remote_session_use_case
    
    def user_repository(self, db_session=None):
        """
        Get user repository with database session.
        
        Args:
            db_session: SQLAlchemy database session (optional, will create if not provided)
            
        Returns:
            UserRepository instance
        """
        if db_session is None:
            db_session = self._db_session_factory()
        return UserRepository(db_session)
    
    def email_service(self) -> EmailService:
        """Get email service instance"""
        return self._email_service
    
    def otp_service(self) -> OTPService:
        """Get OTP service instance"""
        return self._otp_service
    


def setup_dependencies() -> DIContainer:
    """Setup and return dependency injection container"""
    return DIContainer()

