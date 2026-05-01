"""
Chatbot Routes

Routes for chatbot functionality with streaming support.
"""
import logging
import json
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from presentation.middleware.auth_middleware import get_current_user_id
from presentation.middleware.permission_middleware import verify_meeting_permission
from lib.transcript_storage import get_transcript
from application.services.rag_service import RAGService
from application.services.chatbot_agent import ChatbotAgent
from application.services.conversation_memory import ConversationMemory
from core.dependency_injection import setup_dependencies

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user_email(user_id: str = Depends(get_current_user_id)) -> Optional[str]:
    """
    Get current user's email address.
    
    Args:
        user_id: User ID from authentication
        
    Returns:
        User's email address or None if not found
    """
    try:
        container = setup_dependencies()
        # Create an actual session from the sessionmaker
        db_session = container.db_session_factory()()
        try:
            user_repository = container.user_repository(db_session)
            user = user_repository.find_by_id(user_id)
            if user:
                return user.email
            return None
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error getting user email: {e}", exc_info=True)
        return None


class ChatMessageRequest(BaseModel):
    """Request for sending a chat message"""
    message: str
    session_id: str = "default"


class ChatHistoryResponse(BaseModel):
    """Response for chat history"""
    messages: list
    meeting_id: str


def create_chatbot_router() -> APIRouter:
    """
    Create chatbot router with dependencies.
    
    Returns:
        Configured APIRouter
    """
    # Initialize services
    rag_service = RAGService()
    conversation_memory = ConversationMemory()
    
    @router.post("/api/transcripts/{meeting_id}/chat")
    async def send_chat_message(
        meeting_id: str,
        request: ChatMessageRequest,
        user_id: str = Depends(get_current_user_id),
        user_email: Optional[str] = Depends(get_current_user_email)
    ):
        """Send a chat message and get streaming response (requires authentication and ownership)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            logger.info(f"Chat request for transcript {meeting_id} by user: {user_id}")
            
            # Verify chatbot access permission (can_access_meeting + can_use_chatbot)
            transcript_data = verify_meeting_permission(meeting_id, "can_use_chatbot", user_id)
            
            # Track chatbot usage for analytics
            from lib.participant_analytics import track_chatbot_use
            from application.services.permission_service import PermissionService
            permission_service = PermissionService()
            if not permission_service.is_owner(meeting_id, user_id):
                track_chatbot_use(meeting_id, user_id)
            
            # Index transcript if not already indexed
            try:
                rag_service.index_transcript(transcript_data)
            except Exception as e:
                logger.warning(f"Transcript {meeting_id} may already be indexed: {e}")
            
            # Use participant-aware session ID (format: {meeting_id}:{user_id})
            participant_session_id = f"{meeting_id}:{user_id}"
            
            # Get conversation history using participant-aware session
            conversation_history = conversation_memory.get_conversation_context(
                meeting_id,
                participant_session_id,
                max_messages=10
            )
            
            # Create chatbot agent with user email for calendar tools
            agent = ChatbotAgent(rag_service, transcript_data, user_email=user_email)
            
            # Add user message to memory using participant-aware session
            conversation_memory.add_message(
                meeting_id,
                "user",
                request.message,
                participant_session_id
            )
            
            # Stream response
            async def generate_response():
                try:
                    full_response = ""
                    async for chunk in agent.process_message_async(request.message, conversation_history):
                        if chunk:
                            full_response += chunk
                            # Send chunk as SSE
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    
                    # Save assistant response to memory using participant-aware session
                    if full_response:
                        conversation_memory.add_message(
                            meeting_id,
                            "assistant",
                            full_response,
                            participant_session_id
                        )
                        # Send completion signal (without content to avoid duplication)
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                except Exception as e:
                    logger.error(f"Error generating response: {e}", exc_info=True)
                    error_msg = f"Error generating response: {str(e)}"
                    yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            
            return StreamingResponse(
                generate_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process chat message: {str(e)}"
            )
    
    @router.get("/api/transcripts/{meeting_id}/chat/history", response_model=ChatHistoryResponse)
    async def get_chat_history(
        meeting_id: str,
        session_id: str = None,
        user_id: str = Depends(get_current_user_id)
    ):
        """Get conversation history (requires authentication and chatbot access)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            # Verify chatbot access permission
            verify_meeting_permission(meeting_id, "can_use_chatbot", user_id)
            
            # Use participant-aware session ID (format: {meeting_id}:{user_id})
            participant_session_id = session_id if session_id else f"{meeting_id}:{user_id}"
            
            # Get conversation history using participant-aware session
            messages = conversation_memory.get_messages(meeting_id, participant_session_id)
            
            return ChatHistoryResponse(
                messages=messages,
                meeting_id=meeting_id
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting chat history: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get chat history: {str(e)}"
            )
    
    @router.delete("/api/transcripts/{meeting_id}/chat/history")
    async def clear_chat_history(
        meeting_id: str,
        session_id: str = None,
        user_id: str = Depends(get_current_user_id)
    ):
        """Clear conversation history (requires authentication and chatbot access)"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            # Verify chatbot access permission
            verify_meeting_permission(meeting_id, "can_use_chatbot", user_id)
            
            # Use participant-aware session ID (format: {meeting_id}:{user_id})
            participant_session_id = session_id if session_id else f"{meeting_id}:{user_id}"
            
            # Clear conversation using participant-aware session
            conversation_memory.clear_conversation(meeting_id, participant_session_id)
            
            return {"success": True, "message": "Conversation history cleared"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear chat history: {str(e)}"
            )
    
    @router.get("/api/tools")
    async def get_available_tools(
        user_id: str = Depends(get_current_user_id),
        user_email: Optional[str] = Depends(get_current_user_email)
    ):
        """Get list of available tools with descriptions"""
        try:
            tools = [
                {
                    "name": "search_transcript",
                    "description": "Search the transcript for specific information",
                    "category": "transcript"
                },
                {
                    "name": "summarize_transcript",
                    "description": "Get a summary of the transcript",
                    "category": "transcript"
                },
                {
                    "name": "get_speaker_info",
                    "description": "Get information about a specific speaker in the transcript",
                    "category": "transcript"
                },
                {
                    "name": "extract_key_points",
                    "description": "Extract key discussion points from the transcript",
                    "category": "transcript"
                }
            ]
            
            # Check if calendar tools are available
            try:
                from tools.calender import add_event, detect_followup_meetings, search_events
                if user_email and add_event:
                    tools.extend([
                        {
                            "name": "detect_followup_meetings",
                            "description": "Analyze transcript to detect follow-up meetings or scheduled events",
                            "category": "calendar",
                            "parameters": {
                                "transcript_text": "string (optional - uses full transcript if not provided)",
                                "current_date": "string (optional - YYYY-MM-DD format)"
                            }
                        },
                        {
                            "name": "add_event",
                            "description": "Add an event to your Google Calendar",
                            "category": "calendar",
                            "parameters": {
                                "event_summary": "string (required)",
                                "date": "object with year, month, day, hour, minute (required)",
                                "location": "string (optional)",
                                "reminder_before": "integer (optional, default: 15 minutes)",
                                "description": "string (optional)"
                            }
                        },
                        {
                            "name": "search_events",
                            "description": "Search your Google Calendar for events",
                            "category": "calendar",
                            "parameters": {
                                "query": "string (required)",
                                "max_results": "integer (optional, default: 10)"
                            }
                        }
                    ])
            except ImportError:
                logger.info("Calendar tools not available")
            
            return {
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            logger.error(f"Error getting available tools: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get available tools: {str(e)}"
            )
    
    @router.post("/api/tools/calendar/add-event")
    async def trigger_add_calendar_event(
        request: Dict,
        user_id: str = Depends(get_current_user_id),
        user_email: Optional[str] = Depends(get_current_user_email)
    ):
        """Manually trigger adding a calendar event"""
        try:
            if not user_email:
                raise HTTPException(
                    status_code=400,
                    detail="User email not available"
                )
            
            from tools.calender import add_event
            
            event_summary = request.get("event_summary")
            date = request.get("date")
            location = request.get("location", "")
            reminder_before = request.get("reminder_before", 15)
            description = request.get("description", "")
            
            if not event_summary or not date:
                raise HTTPException(
                    status_code=400,
                    detail="event_summary and date are required"
                )
            
            result = add_event.invoke({
                "event_summary": event_summary,
                "date": date,
                "email": user_email,
                "location": location,
                "reminder_before": reminder_before,
                "description": description
            })
            
            return {"success": True, "message": result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding calendar event: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add calendar event: {str(e)}"
            )
    
    @router.post("/api/transcripts/{meeting_id}/detect-meetings")
    async def detect_followup_meetings_endpoint(
        meeting_id: str,
        user_id: str = Depends(get_current_user_id)
    ):
        """Detect follow-up meetings from a transcript"""
        try:
            # URL decode the meeting_id
            from urllib.parse import unquote
            meeting_id = unquote(meeting_id)
            
            # Verify transcript access permission
            from presentation.middleware.permission_middleware import verify_meeting_access
            transcript_data = verify_meeting_access(meeting_id, user_id)
            
            # Build transcript text
            entries = transcript_data.get("transcripts", [])
            transcript_text = "\n".join([
                f"{entry.get('speaker', 'Unknown')}: {entry.get('text', '')}"
                for entry in entries
            ])
            
            # Extract transcript start_time
            transcript_start_date = None
            start_time = transcript_data.get("start_time")
            if start_time:
                try:
                    from datetime import datetime
                    if isinstance(start_time, str):
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        transcript_start_date = dt.strftime("%Y-%m-%d")
                    elif hasattr(start_time, 'strftime'):
                        transcript_start_date = start_time.strftime("%Y-%m-%d")
                except Exception as e:
                    logger.warning(f"Could not parse transcript start_time: {e}")
            
            # Call detect_followup_meetings tool
            from tools.calender import detect_followup_meetings
            
            result_json = detect_followup_meetings.invoke({
                "transcript_text": transcript_text,
                "transcript_start_date": transcript_start_date,
                "current_date": None
            })
            
            result = json.loads(result_json)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error detecting follow-up meetings: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to detect follow-up meetings: {str(e)}"
            )
    
    return router

