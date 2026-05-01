"""
Request DTOs

Data Transfer Objects for incoming API requests.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, constr


class TokenRequest(BaseModel):
    """Request for generating LiveKit access token"""
    room_name: str = Field(..., description="Name of the room to join")
    participant_name: str = Field(..., description="Name of the participant")


class SaveTranscriptRequest(BaseModel):
    """Request for saving a transcript"""
    room_name: str = Field(..., description="Name of the room")


class RegisterRequest(BaseModel):
    """Request for user registration"""
    email: str = Field(..., description="User email address")
    username: str = Field(..., description="User username")
    password: constr(min_length=6, max_length=72) = Field(
        ..., 
        description="User password (6-72 characters, bcrypt limit is 72 bytes)"
    )


class LoginRequest(BaseModel):
    """Request for user login"""
    email_or_username: str = Field(..., description="User email or username")
    password: constr(min_length=1, max_length=72) = Field(
        ..., 
        description="User password (max 72 characters, bcrypt limit is 72 bytes)"
    )


class UpdateTranscriptRequest(BaseModel):
    """Request for updating a transcript"""
    meeting_name: Optional[str] = Field(None, description="New meeting name")
    transcripts: Optional[List[Dict]] = Field(None, description="Updated list of transcript entries")


class RenameSpeakerRequest(BaseModel):
    """Request for renaming a speaker in a transcript"""
    old_speaker: str = Field(..., description="Current speaker name/ID")
    new_speaker: str = Field(..., description="New speaker name/ID")


class AddParticipantRequest(BaseModel):
    """Request for adding a participant to a meeting"""
    email: str = Field(..., description="Email address of the participant (must be registered)")
    role: str = Field(default="viewer", description="Participant role: 'viewer' or 'collaborator'")
    permissions: Optional[Dict[str, bool]] = Field(None, description="Granular permissions (optional, defaults based on role)")


class UpdateParticipantPermissionsRequest(BaseModel):
    """Request for updating participant permissions"""
    permissions: Dict[str, bool] = Field(..., description="Dictionary of permission updates")


class UpdateEmailRequest(BaseModel):
    """Request for updating user email"""
    new_email: str = Field(..., description="New email address")


class UpdateUsernameRequest(BaseModel):
    """Request for updating user username"""
    new_username: str = Field(..., description="New username")


class UpdatePasswordRequest(BaseModel):
    """Request for updating user password"""
    current_password: constr(min_length=1, max_length=72) = Field(..., description="Current password for verification")
    new_password: constr(min_length=6, max_length=72) = Field(..., description="New password (6-72 characters)")


class VerifyEmailRequest(BaseModel):
    """Request for verifying user email with OTP"""
    otp: constr(min_length=6, max_length=6) = Field(..., description="6-digit OTP verification code")


class ResendVerificationRequest(BaseModel):
    """Request for resending verification email (empty body is acceptable)"""
    pass

