"""
Application Configuration

Centralized configuration management.
"""
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(".env.local")


@dataclass
class Config:
    """Application configuration"""
    transcripts_dir: Path
    redis_host: str = "localhost"
    redis_port: int = 6379
    livekit_url: str = "ws://localhost:7880"
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/livetalk"
    )
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = os.environ.get("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    # Remote control configuration
    remote_session_expiry_seconds: int = int(os.environ.get("REMOTE_SESSION_EXPIRY_SECONDS", "300"))  # 5 minutes
    remote_session_active_ttl: int = int(os.environ.get("REMOTE_SESSION_ACTIVE_TTL", "3600"))  # 1 hour
    remote_qr_code_size: int = int(os.environ.get("REMOTE_QR_CODE_SIZE", "300"))
    enable_remote_control: bool = os.environ.get("ENABLE_REMOTE_CONTROL", "true").lower() == "true"


_config: Config = None


def get_config() -> Config:
    """Get application configuration"""
    global _config
    if _config is None:
        transcripts_dir = Path(__file__).parent.parent / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        _config = Config(transcripts_dir=transcripts_dir)
    return _config

