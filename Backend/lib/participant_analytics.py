"""
Participant Analytics

Helper functions for tracking participant engagement and access analytics.
"""
import json
from datetime import datetime
from typing import Dict, Optional
from infrastructure.config.redis_config import get_redis_client


def track_participant_access(meeting_id: str, user_id: str):
    """
    Track participant access to a meeting.
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID
    """
    client = get_redis_client()
    analytics_key = f"meeting:analytics:{meeting_id}:{user_id}"
    
    # Get existing analytics
    data = client.hgetall(analytics_key)
    
    # Update access count and last accessed
    access_count = int(data.get("access_count", 0)) + 1
    last_accessed = datetime.now().isoformat()
    
    client.hset(analytics_key, mapping={
        "access_count": str(access_count),
        "last_accessed": last_accessed,
        "user_id": user_id,
        "meeting_id": meeting_id,
    })
    
    # Set TTL to 1 year
    client.expire(analytics_key, 31536000)


def track_chatbot_use(meeting_id: str, user_id: str):
    """
    Track chatbot usage by a participant.
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID
    """
    client = get_redis_client()
    analytics_key = f"meeting:analytics:{meeting_id}:{user_id}"
    
    # Get existing analytics
    data = client.hgetall(analytics_key)
    
    # Update chatbot uses
    chatbot_uses = int(data.get("chatbot_uses", 0)) + 1
    
    client.hset(analytics_key, "chatbot_uses", str(chatbot_uses))
    
    # Set TTL to 1 year
    client.expire(analytics_key, 31536000)


def track_transcript_view(meeting_id: str, user_id: str):
    """
    Track transcript view by a participant.
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID
    """
    client = get_redis_client()
    analytics_key = f"meeting:analytics:{meeting_id}:{user_id}"
    
    # Get existing analytics
    data = client.hgetall(analytics_key)
    
    # Update transcript views
    transcript_views = int(data.get("transcript_views", 0)) + 1
    
    client.hset(analytics_key, "transcript_views", str(transcript_views))
    
    # Set TTL to 1 year
    client.expire(analytics_key, 31536000)


def get_participant_analytics(meeting_id: str, user_id: str) -> Dict:
    """
    Get analytics for a specific participant.
    
    Args:
        meeting_id: The meeting ID
        user_id: The user ID
        
    Returns:
        Dictionary with analytics data
    """
    client = get_redis_client()
    analytics_key = f"meeting:analytics:{meeting_id}:{user_id}"
    
    data = client.hgetall(analytics_key)
    
    if not data:
        return {
            "access_count": 0,
            "chatbot_uses": 0,
            "transcript_views": 0,
            "last_accessed": None,
        }
    
    return {
        "access_count": int(data.get("access_count", 0)),
        "chatbot_uses": int(data.get("chatbot_uses", 0)),
        "transcript_views": int(data.get("transcript_views", 0)),
        "last_accessed": data.get("last_accessed"),
    }


def get_all_participant_analytics(meeting_id: str) -> Dict[str, Dict]:
    """
    Get analytics for all participants in a meeting.
    
    Args:
        meeting_id: The meeting ID
        
    Returns:
        Dictionary mapping user_id to analytics data
    """
    from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
    
    repository = RedisMeetingParticipantRepository()
    participants = repository.find_by_meeting(meeting_id)
    
    result = {}
    for participant in participants:
        result[participant.user_id] = get_participant_analytics(meeting_id, participant.user_id)
    
    return result

