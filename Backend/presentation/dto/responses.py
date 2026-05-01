"""
Response DTOs

Data Transfer Objects for API responses.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Response containing LiveKit access token"""
    token: str = Field(..., description="JWT access token")
    url: str = Field(..., description="LiveKit server URL")


class SaveTranscriptResponse(BaseModel):
    """Response for transcript save operation"""
    success: bool = Field(..., description="Whether the operation succeeded")
    meeting_id: Optional[str] = Field(None, description="Meeting ID of saved transcript")
    message: str = Field(..., description="Response message")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")


class RegisterResponse(BaseModel):
    """Response for user registration"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="User username")
    email_verified: bool = Field(..., description="Whether email is verified")
    created_at: str = Field(..., description="Account creation timestamp")


class LoginResponse(BaseModel):
    """Response for user login"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="User username")
    email_verified: bool = Field(..., description="Whether email is verified")


class UserResponse(BaseModel):
    """Response for user information"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="User username")
    email_verified: bool = Field(..., description="Whether email is verified")
    created_at: str = Field(..., description="Account creation timestamp")


class ResendVerificationResponse(BaseModel):
    """Response for resending verification email"""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Response message")


class TranscriptResponse(BaseModel):
    """Individual transcript response"""
    meeting_id: str = Field(..., description="Meeting ID")
    meeting_name: str = Field(..., description="Meeting name")
    room_name: str = Field(..., description="Room name")
    start_time: str = Field(..., description="Start time")
    end_time: Optional[str] = Field(None, description="End time")
    transcripts: List[Dict[str, Any]] = Field(..., description="List of transcript entries")
    total_entries: int = Field(..., description="Total number of transcript entries")
    created_at: str = Field(..., description="Creation timestamp")
    user_id: Optional[str] = Field(None, description="User ID who created the transcript")
    participant_count: Optional[int] = Field(0, description="Number of post-meeting participants")
    live_participants: Optional[List[str]] = Field([], description="List of live participants (speakers) from the meeting")


class GetTranscriptsResponse(BaseModel):
    """Response for getting user transcripts"""
    transcripts: List[TranscriptResponse] = Field(..., description="List of transcripts")
    count: int = Field(..., description="Total number of transcripts")


class DeleteTranscriptResponse(BaseModel):
    """Response for deleting a transcript"""
    success: bool = Field(..., description="Whether the deletion succeeded")
    message: str = Field(..., description="Response message")


class ParticipantResponse(BaseModel):
    """Response for participant information"""
    user_id: str = Field(..., description="Participant user ID")
    email: str = Field(..., description="Participant email")
    meeting_id: str = Field(..., description="Meeting ID")
    role: str = Field(..., description="Participant role: 'viewer' or 'collaborator'")
    permissions: Dict[str, bool] = Field(..., description="Granular permissions")
    added_at: str = Field(..., description="When participant was added")
    added_by: str = Field(..., description="User ID who added the participant")
    notifications_enabled: bool = Field(default=True, description="Whether notifications are enabled")
    last_accessed: Optional[str] = Field(None, description="Last access timestamp")


class ParticipantListResponse(BaseModel):
    """Response for listing meeting participants"""
    participants: List[ParticipantResponse] = Field(..., description="List of participants")
    count: int = Field(..., description="Total number of participants")


class AddParticipantResponse(BaseModel):
    """Response for adding a participant"""
    success: bool = Field(..., description="Whether the operation succeeded")
    participant: ParticipantResponse = Field(..., description="Added participant information")
    message: str = Field(..., description="Response message")


class RemoveParticipantResponse(BaseModel):
    """Response for removing a participant"""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Response message")


class UpdateParticipantPermissionsResponse(BaseModel):
    """Response for updating participant permissions"""
    success: bool = Field(..., description="Whether the operation succeeded")
    participant: ParticipantResponse = Field(..., description="Updated participant information")
    message: str = Field(..., description="Response message")

