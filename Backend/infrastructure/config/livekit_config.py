"""
LiveKit Configuration

Manages LiveKit server configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

# LiveKit configuration from environment variables
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

# RTMP Ingress configuration
LIVEKIT_RTMP_ENABLED = os.environ.get("LIVEKIT_RTMP_ENABLED", "true").lower() == "true"
LIVEKIT_RTMP_PORT = int(os.environ.get("LIVEKIT_RTMP_PORT", "1935"))


def get_livekit_url() -> str:
    """Get LiveKit server URL"""
    return LIVEKIT_URL


def get_livekit_api_key() -> str:
    """Get LiveKit API key"""
    if not LIVEKIT_API_KEY:
        raise ValueError("LIVEKIT_API_KEY not configured in environment")
    return LIVEKIT_API_KEY


def get_livekit_api_secret() -> str:
    """Get LiveKit API secret"""
    if not LIVEKIT_API_SECRET:
        raise ValueError("LIVEKIT_API_SECRET not configured in environment")
    return LIVEKIT_API_SECRET


def is_rtmp_enabled() -> bool:
    """Check if RTMP ingress is enabled"""
    return LIVEKIT_RTMP_ENABLED


def get_rtmp_port() -> int:
    """Get RTMP port number"""
    return LIVEKIT_RTMP_PORT

