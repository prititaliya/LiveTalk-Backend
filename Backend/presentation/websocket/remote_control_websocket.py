"""
Remote Control WebSocket Handler

Handles WebSocket connections for remote recording control with bidirectional communication.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from application.services.remote_control_service import RemoteControlService
from application.services.recording_state_service import RecordingStateService

logger = logging.getLogger(__name__)


class RemoteControlConnectionManager:
    """Manages WebSocket connections for remote control"""
    
    def __init__(self):
        # Track connections by session_id and device type
        # Structure: {session_id: {"laptop": {websocket1, ...}, "mobile": {websocket2, ...}}}
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # Track device type for each websocket
        self.websocket_metadata: Dict[WebSocket, Dict[str, str]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        device_type: str
    ):
        """
        Connect a WebSocket for a session.
        
        Args:
            websocket: WebSocket connection
            session_id: Session ID
            device_type: Device type ('laptop' or 'mobile')
        """
        try:
            await websocket.accept()
            
            if session_id not in self.active_connections:
                self.active_connections[session_id] = {"laptop": set(), "mobile": set()}
            
            if device_type not in self.active_connections[session_id]:
                self.active_connections[session_id][device_type] = set()
            
            self.active_connections[session_id][device_type].add(websocket)
            self.websocket_metadata[websocket] = {
                "session_id": session_id,
                "device_type": device_type
            }
            
            logger.info(f"WebSocket connected for session {session_id}, device: {device_type}")
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket not in self.websocket_metadata:
            return
        
        metadata = self.websocket_metadata[websocket]
        session_id = metadata["session_id"]
        device_type = metadata["device_type"]
        
        if session_id in self.active_connections:
            if device_type in self.active_connections[session_id]:
                self.active_connections[session_id][device_type].discard(websocket)
                
                # Clean up empty sets
                if not self.active_connections[session_id][device_type]:
                    del self.active_connections[session_id][device_type]
                
                # Clean up empty sessions
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
        
        del self.websocket_metadata[websocket]
        logger.info(f"WebSocket disconnected for session {session_id}, device: {device_type}")
    
    async def broadcast_recording_state(
        self,
        session_id: str,
        state: str,
        source_device: str,
        timestamp: Optional[str] = None
    ):
        """
        Broadcast recording state update to all connected devices for a session.
        
        Args:
            session_id: Session ID
            state: Recording state ('idle', 'recording', 'paused', 'stopped')
            source_device: Source device ('laptop' or 'mobile')
            timestamp: Optional timestamp
        """
        if session_id not in self.active_connections:
            return
        
        timestamp = timestamp or datetime.now().isoformat()
        message = {
            "type": "recording_state_update",
            "session_id": session_id,
            "state": state,
            "timestamp": timestamp,
            "source_device": source_device
        }
        
        disconnected = set()
        
        # Broadcast to all devices (laptop and mobile)
        for device_type, connections in self.active_connections[session_id].items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending state update to {device_type}: {e}")
                    disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to a specific WebSocket"""
        try:
            await websocket.send_json({
                "type": "error",
                "message": error_message
            })
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


class RemoteControlWebSocketManager:
    """Manages WebSocket connections for remote control"""
    
    def __init__(
        self,
        remote_control_service: RemoteControlService,
        recording_state_service: RecordingStateService
    ):
        """
        Initialize remote control WebSocket manager.
        
        Args:
            remote_control_service: Service for remote control operations
            recording_state_service: Service for recording state management
        """
        self.connection_manager = RemoteControlConnectionManager()
        self.remote_control_service = remote_control_service
        self.recording_state_service = recording_state_service
    
    async def handle_websocket(
        self,
        websocket: WebSocket,
        session_token: str,
        device_type: str = "laptop"
    ):
        """
        Handle WebSocket connection for remote control.
        
        Args:
            websocket: WebSocket connection
            session_token: Session token
            device_type: Device type ('laptop' or 'mobile')
        """
        session = None
        try:
            # Validate session token
            session = self.remote_control_service.validate_remote_session(session_token)
            if not session:
                await websocket.close(code=4001, reason="Invalid or expired session token")
                return
            
            # Connect WebSocket
            await self.connection_manager.connect(websocket, session.session_id, device_type)
            
            # Add device to session
            self.remote_control_service.remote_session_repository.add_connected_device(
                session.session_id,
                device_type
            )
            
            # Send initial state
            recording_state = self.remote_control_service.get_recording_state(session.session_id)
            await websocket.send_json({
                "type": "connection_established",
                "session_id": session.session_id,
                "room_name": session.room_name,
                "recording_state": recording_state
            })
            
            # Handle incoming messages
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError:
                        await self.connection_manager.send_error(
                            websocket,
                            "Invalid JSON format"
                        )
                        continue
                    
                    # Handle message types
                    message_type = message.get("type")
                    
                    if message_type == "remote_command":
                        await self._handle_remote_command(
                            websocket,
                            session.session_id,
                            message,
                            device_type
                        )
                    elif message_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    else:
                        await self.connection_manager.send_error(
                            websocket,
                            f"Unknown message type: {message_type}"
                        )
                        
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for session {session.session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
                    await self.connection_manager.send_error(
                        websocket,
                        f"Error processing message: {str(e)}"
                    )
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            if session:
                # Remove device from session
                self.remote_control_service.disconnect_remote_session(
                    session.session_id,
                    device_type
                )
            self.connection_manager.disconnect(websocket)
    
    async def _handle_remote_command(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict,
        source_device: str
    ):
        """
        Handle a remote command.
        
        Args:
            websocket: WebSocket connection
            session_id: Session ID
            message: Message dictionary
            source_device: Source device type
        """
        command = message.get("command")
        if not command:
            await self.connection_manager.send_error(websocket, "Command is required")
            return
        
        # Execute command
        result = self.remote_control_service.handle_remote_command(
            session_id=session_id,
            command=command,
            source_device=source_device
        )
        
        # Send response to sender
        await websocket.send_json({
            "type": "command_response",
            "success": result["success"],
            "message": result["message"],
            "state": result["state"]
        })
        
        # Broadcast state update to all connected devices
        if result["success"]:
            await self.connection_manager.broadcast_recording_state(
                session_id=session_id,
                state=result["state"],
                source_device=source_device
            )
    
    async def broadcast_state_change(
        self,
        session_id: str,
        state: str,
        source: str
    ):
        """
        Broadcast state change from external source (e.g., agent).
        
        Args:
            session_id: Session ID
            state: New recording state
            source: Source of change
        """
        await self.connection_manager.broadcast_recording_state(
            session_id=session_id,
            state=state,
            source_device=source
        )

