"""
FastAPI Application

Main API entry point using the 5-tier architecture.
"""
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket

logger = logging.getLogger(__name__)

from core.dependency_injection import setup_dependencies
from presentation.middleware.cors_middleware import configure_cors
from presentation.api.routes.health_routes import router as health_router
from presentation.api.routes.token_routes import create_token_router
from presentation.api.routes.transcript_routes import create_transcript_router
from presentation.api.routes.auth_routes import create_auth_router
from presentation.api.routes.chatbot_routes import create_chatbot_router
from presentation.api.routes.remote_control_routes import create_remote_control_router
from presentation.api.routes.participant_routes import create_participant_router
from presentation.websocket.transcript_websocket import TranscriptWebSocketManager
from presentation.websocket.remote_control_websocket import RemoteControlWebSocketManager
from infrastructure.database.database import init_db

# Setup dependency injection
container = setup_dependencies()

# Create FastAPI app
app = FastAPI(title="LiveTalk API")

# Configure CORS
configure_cors(app)

# Get dependencies from container
generate_token_use_case = container.generate_token_use_case()
save_transcript_use_case = container.save_transcript_use_case()
file_storage = container.file_storage()
transcripts_dir = Path(__file__).parent / "transcripts"
transcripts_dir.mkdir(exist_ok=True)

# Setup WebSocket managers
websocket_manager = TranscriptWebSocketManager(file_storage, transcripts_dir)
remote_control_websocket_manager = RemoteControlWebSocketManager(
    remote_control_service=container.remote_control_service(),
    recording_state_service=container.recording_state_service()
)

# Register routes
# Health router with /api prefix
app.include_router(health_router, prefix="/api", tags=["health"])
# Also register health at root level for backward compatibility
app.include_router(health_router, tags=["health"])
app.include_router(create_token_router(generate_token_use_case))
app.include_router(create_transcript_router(save_transcript_use_case, transcripts_dir))
app.include_router(create_auth_router(container))
app.include_router(create_chatbot_router())
app.include_router(create_remote_control_router(
    generate_remote_session_use_case=container.generate_remote_session_use_case(),
    remote_control_service=container.remote_control_service()
))
app.include_router(create_participant_router())

# WebSocket endpoints
@app.websocket("/ws/transcripts/{room_name}")
async def websocket_transcripts(websocket: WebSocket, room_name: str):
    """WebSocket endpoint for real-time transcript updates"""
    logger.info(f"WebSocket endpoint called for room: {room_name}")
    try:
        await websocket_manager.handle_websocket(websocket, room_name)
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}", exc_info=True)
        raise


@app.websocket("/ws/remote/{session_token}")
async def websocket_remote_control(websocket: WebSocket, session_token: str):
    """WebSocket endpoint for remote recording control"""
    logger.info(f"Remote control WebSocket endpoint called for session token")
    try:
        # Determine device type from query parameter or default to laptop
        # Mobile devices should pass ?device=mobile
        device_type = "mobile" if "mobile" in str(websocket.url.query).lower() else "laptop"
        await remote_control_websocket_manager.handle_websocket(
            websocket,
            session_token,
            device_type=device_type
        )
    except Exception as e:
        logger.error(f"Remote control WebSocket endpoint error: {e}", exc_info=True)
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup"""
    # Initialize database tables
    init_db()
    # Start file watcher
    loop = asyncio.get_event_loop()
    websocket_manager.start_file_watcher(loop)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    websocket_manager.stop_file_watcher()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

