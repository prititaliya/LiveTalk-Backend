"""
Conversation Memory Service

Manages conversation history for chatbot sessions using Redis.
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from lib.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Service for managing conversation memory in Redis"""
    
    def __init__(self, ttl_hours: int = 24):
        """
        Initialize conversation memory service.
        
        Args:
            ttl_hours: Time to live for conversations in hours (default: 24)
        """
        self.ttl_seconds = ttl_hours * 3600
        logger.info(f"Initialized ConversationMemory with TTL: {ttl_hours} hours")
    
    def _get_conversation_key(self, meeting_id: str, session_id: Optional[str] = None) -> str:
        """
        Generate Redis key for conversation.
        
        Args:
            meeting_id: The meeting ID
            session_id: Optional session ID (defaults to 'default')
            
        Returns:
            Redis key string
        """
        session = session_id or "default"
        return f"conversation:{meeting_id}:{session}"
    
    def add_message(
        self,
        meeting_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None
    ) -> None:
        """
        Add a message to conversation history.
        
        Args:
            meeting_id: The meeting ID
            role: Message role ('user' or 'assistant')
            content: Message content
            session_id: Optional session ID
        """
        if role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'")
        
        client = get_redis_client()
        key = self._get_conversation_key(meeting_id, session_id)
        
        # Get existing messages
        messages = self.get_messages(meeting_id, session_id)
        
        # Add new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        messages.append(message)
        
        # Store back to Redis
        client.setex(
            key,
            self.ttl_seconds,
            json.dumps(messages)
        )
        
        logger.debug(f"Added {role} message to conversation {meeting_id}:{session_id or 'default'}")
    
    def get_messages(
        self,
        meeting_id: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get conversation history.
        
        Args:
            meeting_id: The meeting ID
            session_id: Optional session ID
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dictionaries
        """
        client = get_redis_client()
        key = self._get_conversation_key(meeting_id, session_id)
        
        data = client.get(key)
        if not data:
            return []
        
        try:
            messages = json.loads(data)
            if limit:
                # Return most recent messages
                messages = messages[-limit:]
            return messages
        except json.JSONDecodeError:
            logger.error(f"Error decoding conversation messages for {key}")
            return []
    
    def get_conversation_context(
        self,
        meeting_id: str,
        session_id: Optional[str] = None,
        max_messages: int = 10
    ) -> List[Dict]:
        """
        Get conversation context for LLM (last N messages).
        
        Args:
            meeting_id: The meeting ID
            session_id: Optional session ID
            max_messages: Maximum number of messages to return
            
        Returns:
            List of message dictionaries formatted for LLM
        """
        messages = self.get_messages(meeting_id, session_id, limit=max_messages)
        
        # Format for LangChain/LangGraph
        context = []
        for msg in messages:
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return context
    
    def clear_conversation(
        self,
        meeting_id: str,
        session_id: Optional[str] = None
    ) -> None:
        """
        Clear conversation history.
        
        Args:
            meeting_id: The meeting ID
            session_id: Optional session ID
        """
        client = get_redis_client()
        key = self._get_conversation_key(meeting_id, session_id)
        
        client.delete(key)
        logger.info(f"Cleared conversation history for {meeting_id}:{session_id or 'default'}")
    
    def conversation_exists(
        self,
        meeting_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Check if conversation exists.
        
        Args:
            meeting_id: The meeting ID
            session_id: Optional session ID
            
        Returns:
            True if conversation exists, False otherwise
        """
        client = get_redis_client()
        key = self._get_conversation_key(meeting_id, session_id)
        
        return client.exists(key) > 0

