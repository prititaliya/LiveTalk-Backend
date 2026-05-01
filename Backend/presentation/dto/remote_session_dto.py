"""
Remote Session DTOs

Data Transfer Objects for remote recording control requests and responses.
"""
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class GenerateSessionRequest(BaseModel):
    """Request for generating a remote session"""
    room_name: str = Field(..., description="Name of the room for recording")
    user_id: Optional[str] = Field(None, description="User ID (optional, can be extracted from JWT)")


class GenerateSessionResponse(BaseModel):
    """Response containing remote session details and QR code"""
    session_token: str = Field(..., description="Session token for remote access")
    qr_code_data: str = Field(..., description="Base64-encoded QR code image data")
    expires_at: str = Field(..., description="Session expiration timestamp (ISO format)")
    session_id: str = Field(..., description="Session ID")


class SessionStatusResponse(BaseModel):
    """Response containing session status information"""
    room_name: str = Field(..., description="Room name")
    status: str = Field(..., description="Session status (pending/active/expired)")
    recording_state: Dict = Field(..., description="Current recording state information")
    expires_at: str = Field(..., description="Session expiration timestamp (ISO format)")
    connected_devices: List[str] = Field(default_factory=list, description="List of connected devices")


class RemoteCommandRequest(BaseModel):
    """Request for executing a remote command"""
    command: str = Field(..., description="Command to execute (start_recording, stop_recording, pause_recording, resume_recording, end_session)")
    payload: Optional[Dict] = Field(None, description="Optional command payload")


class RemoteCommandResponse(BaseModel):
    """Response for remote command execution"""
    success: bool = Field(..., description="Whether the command executed successfully")
    message: str = Field(..., description="Response message")
    state: str = Field(..., description="Current recording state after command execution")

