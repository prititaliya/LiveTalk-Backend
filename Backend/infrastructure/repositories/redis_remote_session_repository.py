"""
Redis Remote Session Repository Implementation

Implements IRemoteSessionRepository interface using Redis as the storage backend.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

from domain.interfaces.remote_session_repository import IRemoteSessionRepository
from domain.entities.remote_session import RemoteSession
from infrastructure.config.redis_config import get_redis_client

logger = logging.getLogger(__name__)


class RedisRemoteSessionRepository(IRemoteSessionRepository):
    """Redis implementation of remote session repository"""
    
    def _get_redis_key(self, session_id: str) -> str:
        """Get Redis key for a session"""
        return f"remote_session:{session_id}"
    
    def _get_token_key(self, token: str) -> str:
        """Get Redis key for token lookup"""
        return f"remote_session_token:{token}"
    
    def _get_devices_key(self, session_id: str) -> str:
        """Get Redis key for connected devices set"""
        return f"remote_session_devices:{session_id}"
    
    def create_session(self, session: RemoteSession) -> str:
        """Create a new remote session in Redis"""
        client = get_redis_client()
        redis_key = self._get_redis_key(session.session_id)
        
        # Calculate TTL in seconds
        ttl_seconds = int((session.expires_at - datetime.now()).total_seconds())
        if ttl_seconds <= 0:
            raise ValueError("Session expiration time must be in the future")
        
        # Prepare session data
        session_data = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "room_name": session.room_name,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "status": session.status,
            "recording_state": session.recording_state,
            "session_token": session.session_token or "",
        }
        
        # Store session data as hash
        client.hset(redis_key, mapping=session_data)
        
        # Set TTL
        client.expire(redis_key, ttl_seconds)
        
        # Store token mapping if token exists
        if session.session_token:
            token_key = self._get_token_key(session.session_token)
            client.setex(token_key, ttl_seconds, session.session_id)
        
        # Initialize connected devices set
        devices_key = self._get_devices_key(session.session_id)
        if session.connected_devices:
            for device in session.connected_devices:
                client.sadd(devices_key, device)
        client.expire(devices_key, ttl_seconds)
        
        logger.info(f"Created remote session {session.session_id} with TTL {ttl_seconds}s")
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[RemoteSession]:
        """Get a remote session by session ID"""
        client = get_redis_client()
        redis_key = self._get_redis_key(session_id)
        
        # Get session data
        data = client.hgetall(redis_key)
        if not data:
            return None
        
        # Get connected devices
        devices_key = self._get_devices_key(session_id)
        devices = client.smembers(devices_key)
        
        try:
            return RemoteSession(
                session_id=data["session_id"],
                user_id=data["user_id"],
                room_name=data["room_name"],
                created_at=datetime.fromisoformat(data["created_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]),
                status=data["status"],
                connected_devices=set(devices) if devices else set(),
                recording_state=data.get("recording_state", "idle"),
                session_token=data.get("session_token") or None,
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing remote session data: {e}")
            return None
    
    def get_session_by_token(self, token: str) -> Optional[RemoteSession]:
        """Get a remote session by session token"""
        client = get_redis_client()
        token_key = self._get_token_key(token)
        
        # Get session_id from token
        session_id = client.get(token_key)
        if not session_id:
            return None
        
        # Get session by ID
        return self.get_session(session_id)
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update the status of a remote session"""
        if status not in ['pending', 'active', 'expired']:
            logger.error(f"Invalid status: {status}")
            return False
        
        client = get_redis_client()
        redis_key = self._get_redis_key(session_id)
        
        if not client.exists(redis_key):
            logger.warning(f"Session {session_id} not found")
            return False
        
        client.hset(redis_key, "status", status)
        logger.debug(f"Updated session {session_id} status to {status}")
        return True
    
    def update_recording_state(self, session_id: str, state: str) -> bool:
        """Update the recording state of a remote session"""
        if state not in ['idle', 'recording', 'paused', 'stopped']:
            logger.error(f"Invalid recording state: {state}")
            return False
        
        client = get_redis_client()
        redis_key = self._get_redis_key(session_id)
        
        if not client.exists(redis_key):
            logger.warning(f"Session {session_id} not found")
            return False
        
        client.hset(redis_key, "recording_state", state)
        logger.debug(f"Updated session {session_id} recording state to {state}")
        return True
    
    def add_connected_device(self, session_id: str, device: str) -> bool:
        """Add a connected device to the session"""
        if device not in ['laptop', 'mobile']:
            logger.error(f"Invalid device type: {device}")
            return False
        
        client = get_redis_client()
        devices_key = self._get_devices_key(session_id)
        redis_key = self._get_redis_key(session_id)
        
        if not client.exists(redis_key):
            logger.warning(f"Session {session_id} not found")
            return False
        
        # Add device to set
        client.sadd(devices_key, device)
        
        # Update status to active if pending
        current_status = client.hget(redis_key, "status")
        if current_status == "pending":
            self.update_session_status(session_id, "active")
        
        logger.debug(f"Added device {device} to session {session_id}")
        return True
    
    def remove_connected_device(self, session_id: str, device: str) -> bool:
        """Remove a connected device from the session"""
        client = get_redis_client()
        devices_key = self._get_devices_key(session_id)
        redis_key = self._get_redis_key(session_id)
        
        if not client.exists(redis_key):
            logger.warning(f"Session {session_id} not found")
            return False
        
        # Remove device from set
        client.srem(devices_key, device)
        
        # Check if no devices left
        remaining_devices = client.smembers(devices_key)
        if not remaining_devices:
            self.update_session_status(session_id, "expired")
        
        logger.debug(f"Removed device {device} from session {session_id}")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a remote session"""
        client = get_redis_client()
        redis_key = self._get_redis_key(session_id)
        devices_key = self._get_devices_key(session_id)
        
        # Get token before deleting
        token = client.hget(redis_key, "session_token")
        
        # Delete session data
        deleted = client.delete(redis_key) > 0
        
        # Delete devices set
        client.delete(devices_key)
        
        # Delete token mapping if exists
        if token:
            token_key = self._get_token_key(token)
            client.delete(token_key)
        
        if deleted:
            logger.info(f"Deleted remote session {session_id}")
        else:
            logger.warning(f"Session {session_id} not found for deletion")
        
        return deleted

