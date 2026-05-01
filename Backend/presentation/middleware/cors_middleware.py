"""
CORS Middleware Configuration

Configures CORS for the FastAPI application.
Supports localhost and external URLs (e.g., ngrok).
"""
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv(".env.local")


def configure_cors(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI app.
    Allows localhost and external origins (e.g., ngrok URLs).
    
    Args:
        app: FastAPI application instance
    """
    # Get allowed origins from environment or use defaults
    allowed_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    
    # Default localhost origins
    default_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # Parse allowed origins from environment variable
    # Format: "http://localhost:3000,https://example.ngrok.io,https://another-domain.com"
    if allowed_origins_env:
        allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
        # Combine with defaults
        allowed_origins = list(set(default_origins + allowed_origins))
    else:
        allowed_origins = default_origins
    
    # If ALLOW_ALL_ORIGINS is set to "true", allow all origins (for development)
    allow_all_origins = os.environ.get("ALLOW_ALL_ORIGINS", "false").lower() == "true"
    
    # Log CORS configuration for debugging
    import logging
    logger = logging.getLogger(__name__)
    if allow_all_origins:
        logger.info("CORS: Allowing all origins (ALLOW_ALL_ORIGINS=true)")
    else:
        logger.info(f"CORS: Allowed origins: {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
        expose_headers=["*"],
    )

