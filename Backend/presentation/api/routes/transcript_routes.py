"""
Transcript Routes

Routes for transcript operations.
"""
import logging
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends
from presentation.dto.requests import SaveTranscriptRequest, UpdateTranscriptRequest, RenameSpeakerRequest
from presentation.dto.responses import SaveTranscriptResponse, GetTranscriptsResponse, TranscriptResponse, DeleteTranscriptResponse
from application.use_cases.save_transcript import SaveTranscriptUseCase
from presentation.middleware.auth_middleware import get_current_user_id
from presentation.middleware.permission_middleware import verify_meeting_access, verify_meeting_ownership
from lib.transcript_storage import get_transcripts_by_user_id, get_transcript, update_transcript, rename_speaker_in_transcript, delete_transcript
from infrastructure.config.redis_config import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


def create_transcript_router(
    save_transcript_use_case: SaveTranscriptUseCase,
    transcripts_dir: Path
) -> APIRouter:
    """
    Create transcript router with dependencies.
    
    Args:
        save_transcript_use_case: Use case for saving transcripts
        transcripts_dir: Directory containing transcript files
        
    Returns:
        Configured APIRouter
    """
    @router.post("/api/transcripts/save", response_model=SaveTranscriptResponse)
    async def save_transcript(
        request: SaveTranscriptRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """Save transcript to Redis when recording stops (requires authentication)"""
        try:
            room_name = request.room_name
            
            # Find the transcript JSON file for this room
            transcript_file = None
            for file in transcripts_dir.glob(f"{room_name}_*.json"):
                transcript_file = file
                break
            
            if not transcript_file or not transcript_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Transcript file not found for room: {room_name}"
                )
            
            # Save transcript with user_id
            meeting_id = save_transcript_use_case.execute(room_name, transcript_file, user_id)
            
            return SaveTranscriptResponse(
                success=True,
                meeting_id=meeting_id.value,
                message=f"Transcript saved successfully with meeting ID: {meeting_id.value}"
            )
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process transcript: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving transcript: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error saving transcript: {str(e)}"
            )
    
    @router.get("/api/transcripts", response_model=GetTranscriptsResponse)
    async def get_user_transcripts(
        user_id: str = Depends(get_current_user_id)
    ):
        """Get all transcripts accessible to the authenticated user (requires authentication)"""
        try:
            from application.services.permission_service import PermissionService
            
            logger.info(f"Fetching transcripts for user: {user_id}")
            
            permission_service = PermissionService()
            
            # Get all transcripts the user owns
            owned_transcripts = get_transcripts_by_user_id(user_id)
            
            # Get all meetings where this user is a participant
            # Note: This scans all meetings - in production, consider adding a reverse index
            # like `participants:by_user:{user_id}` set for better performance
            client = get_redis_client()
            all_existing_meetings = client.smembers("transcripts:all")
            
            participant_meetings = []
            for meeting_id in all_existing_meetings:
                # Quick check: see if user_id is in the participants set for this meeting
                participants_set_key = f"meeting:participants:{meeting_id}"
                if client.sismember(participants_set_key, user_id):
                    participant_meetings.append(meeting_id)
            
            # Fetch transcripts for participant meetings
            participant_transcripts = []
            for meeting_id in participant_meetings:
                transcript_data = get_transcript(meeting_id)
                if transcript_data:
                    participant_transcripts.append(transcript_data)
            
            # Combine owned and participant transcripts, avoiding duplicates
            accessible_transcripts = set()
            transcript_responses = []
            
            # Add owned transcripts
            for transcript_data in owned_transcripts:
                meeting_id = transcript_data.get("meeting_id", "")
                if meeting_id:
                    accessible_transcripts.add(meeting_id)
                    transcript_responses.append(
                        TranscriptResponse(
                            meeting_id=meeting_id,
                            meeting_name=transcript_data.get("meeting_name", ""),
                            room_name=transcript_data.get("room_name", ""),
                            start_time=transcript_data.get("start_time", ""),
                            end_time=transcript_data.get("end_time"),
                            transcripts=transcript_data.get("transcripts", []),
                            total_entries=transcript_data.get("total_entries", 0),
                            created_at=transcript_data.get("created_at", ""),
                            user_id=transcript_data.get("user_id"),
                            participant_count=transcript_data.get("participant_count", 0),
                            live_participants=transcript_data.get("live_participants", []),
                        )
                    )
            
            # Add participant transcripts (skip if already added as owned)
            for transcript_data in participant_transcripts:
                meeting_id = transcript_data.get("meeting_id", "")
                if meeting_id and meeting_id not in accessible_transcripts:
                    accessible_transcripts.add(meeting_id)
                    transcript_responses.append(
                        TranscriptResponse(
                            meeting_id=meeting_id,
                            meeting_name=transcript_data.get("meeting_name", ""),
                            room_name=transcript_data.get("room_name", ""),
                            start_time=transcript_data.get("start_time", ""),
                            end_time=transcript_data.get("end_time"),
                            transcripts=transcript_data.get("transcripts", []),
                            total_entries=transcript_data.get("total_entries", 0),
                            created_at=transcript_data.get("created_at", ""),
                            user_id=transcript_data.get("user_id"),
                            participant_count=transcript_data.get("participant_count", 0),
                            live_participants=transcript_data.get("live_participants", []),
                        )
                    )
            
            # Sort by start_time (most recent first)
            transcript_responses.sort(key=lambda x: x.start_time, reverse=True)
            
            logger.info(f"Returning {len(transcript_responses)} accessible transcripts for user: {user_id} ({len(owned_transcripts)} owned, {len(participant_transcripts)} as participant)")
            
            return GetTranscriptsResponse(
                transcripts=transcript_responses,
                count=len(transcript_responses)
            )
        except Exception as e:
            logger.error(f"Error fetching user transcripts: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch transcripts: {str(e)}"
            )
    
    @router.delete("/api/transcripts/{meeting_id}", response_model=DeleteTranscriptResponse)
    async def delete_user_transcript(
        meeting_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """Delete a transcript (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id in case it was encoded
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Delete request for transcript {meeting_id} by user: {user_id}")
            
            # Verify ownership (only owners can delete)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Delete transcript
            deleted = delete_transcript(meeting_id)
            
            if not deleted:
                logger.error(f"Failed to delete transcript {meeting_id} - delete_transcript returned False")
                raise HTTPException(
                    status_code=404,
                    detail=f"Transcript not found: {meeting_id}"
                )
            
            logger.info(f"Successfully deleted transcript {meeting_id} for user: {user_id}")
            
            return DeleteTranscriptResponse(
                success=True,
                message=f"Transcript {meeting_id} deleted successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting transcript: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete transcript: {str(e)}"
            )
    
    @router.put("/api/transcripts/{meeting_id}", response_model=TranscriptResponse)
    async def update_user_transcript(
        meeting_id: str,
        request: UpdateTranscriptRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """Update a transcript (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id in case it was encoded
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Updating transcript {meeting_id} for user: {user_id}")
            
            # Verify ownership (only owners can update)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Update transcript
            updated_transcript = update_transcript(
                meeting_id=meeting_id,
                meeting_name=request.meeting_name,
                transcripts=request.transcripts
            )
            
            if not updated_transcript:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transcript not found: {meeting_id}"
                )
            
            logger.info(f"Successfully updated transcript {meeting_id} for user: {user_id}")
            
            # Convert to response format
            return TranscriptResponse(
                meeting_id=updated_transcript.get("meeting_id", ""),
                meeting_name=updated_transcript.get("meeting_name", ""),
                room_name=updated_transcript.get("room_name", ""),
                start_time=updated_transcript.get("start_time", ""),
                end_time=updated_transcript.get("end_time"),
                transcripts=updated_transcript.get("transcripts", []),
                total_entries=updated_transcript.get("total_entries", 0),
                created_at=updated_transcript.get("created_at", ""),
                user_id=updated_transcript.get("user_id"),
                participant_count=updated_transcript.get("participant_count", 0),
                live_participants=updated_transcript.get("live_participants", []),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating transcript: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update transcript: {str(e)}"
            )
    
    @router.patch("/api/transcripts/{meeting_id}/speaker", response_model=TranscriptResponse)
    async def rename_speaker(
        meeting_id: str,
        request: RenameSpeakerRequest,
        user_id: str = Depends(get_current_user_id)
    ):
        """Rename a speaker across all entries in a transcript (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id in case it was encoded
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Renaming speaker in transcript {meeting_id} for user: {user_id}")
            
            # Verify ownership (only owners can rename speakers)
            verify_meeting_ownership(meeting_id, user_id)
            
            # Rename speaker
            updated_transcript = rename_speaker_in_transcript(
                meeting_id=meeting_id,
                old_speaker=request.old_speaker,
                new_speaker=request.new_speaker
            )
            
            if not updated_transcript:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transcript not found: {meeting_id}"
                )
            
            logger.info(f"Successfully renamed speaker in transcript {meeting_id} for user: {user_id}")
            
            # Convert to response format
            return TranscriptResponse(
                meeting_id=updated_transcript.get("meeting_id", ""),
                meeting_name=updated_transcript.get("meeting_name", ""),
                room_name=updated_transcript.get("room_name", ""),
                start_time=updated_transcript.get("start_time", ""),
                end_time=updated_transcript.get("end_time"),
                transcripts=updated_transcript.get("transcripts", []),
                total_entries=updated_transcript.get("total_entries", 0),
                created_at=updated_transcript.get("created_at", ""),
                user_id=updated_transcript.get("user_id"),
                participant_count=updated_transcript.get("participant_count", 0),
                live_participants=updated_transcript.get("live_participants", []),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error renaming speaker: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to rename speaker: {str(e)}"
            )
    
    return router

