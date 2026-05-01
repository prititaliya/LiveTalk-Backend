"""
Redis Meeting Participant Repository Implementation

Implements IMeetingParticipantRepository interface using Redis as the storage backend.
"""
import json
from datetime import datetime
from typing import List, Optional, Dict

from domain.interfaces.meeting_participant_repository import IMeetingParticipantRepository
from domain.entities.meeting_participant import MeetingParticipant
from infrastructure.config.redis_config import get_redis_client


class RedisMeetingParticipantRepository(IMeetingParticipantRepository):
    """Redis implementation of meeting participant repository"""
    
    def add(self, participant: MeetingParticipant) -> MeetingParticipant:
        """Add a participant to a meeting"""
        client = get_redis_client()
        
        # Check if participant already exists
        existing = self.find_by_user_and_meeting(participant.meeting_id, participant.user_id)
        if existing:
            raise ValueError(f"Participant {participant.user_id} already exists in meeting {participant.meeting_id}")
        
        # Store participant details in hash
        participant_key = f"meeting:participant:{participant.meeting_id}:{participant.user_id}"
        hash_data = {
            "user_id": participant.user_id,
            "email": participant.email,
            "meeting_id": participant.meeting_id,
            "role": participant.role,
            "added_at": participant.added_at.isoformat(),
            "added_by": participant.added_by,
            "permissions": json.dumps(participant.permissions),
            "notifications_enabled": str(participant.notifications_enabled),
            "last_accessed": participant.last_accessed.isoformat() if participant.last_accessed else None,
        }
        client.hset(participant_key, mapping={k: v for k, v in hash_data.items() if v is not None})
        
        # Add user_id to participants set
        participants_set_key = f"meeting:participants:{participant.meeting_id}"
        client.sadd(participants_set_key, participant.user_id)
        
        # Update participant count in meeting hash
        meeting_key = f"transcript:{participant.meeting_id}"
        participant_count = self.count_by_meeting(participant.meeting_id)
        client.hset(meeting_key, "participant_count", str(participant_count))
        
        # Update last_accessed field if it was set
        if participant.last_accessed:
            client.hset(participant_key, "last_accessed", participant.last_accessed.isoformat())
        
        return participant
    
    def remove(self, meeting_id: str, user_id: str) -> bool:
        """Remove a participant from a meeting"""
        client = get_redis_client()
        
        # Check if participant exists
        participant_key = f"meeting:participant:{meeting_id}:{user_id}"
        if not client.exists(participant_key):
            return False
        
        # Remove from participants set
        participants_set_key = f"meeting:participants:{meeting_id}"
        client.srem(participants_set_key, user_id)
        
        # Delete participant hash
        client.delete(participant_key)
        
        # Update participant count in meeting hash
        meeting_key = f"transcript:{meeting_id}"
        participant_count = self.count_by_meeting(meeting_id)
        client.hset(meeting_key, "participant_count", str(participant_count))
        
        return True
    
    def find_by_meeting(self, meeting_id: str) -> List[MeetingParticipant]:
        """Find all participants for a meeting"""
        client = get_redis_client()
        
        participants_set_key = f"meeting:participants:{meeting_id}"
        user_ids = client.smembers(participants_set_key)
        
        participants = []
        for user_id in user_ids:
            participant = self.find_by_user_and_meeting(meeting_id, user_id)
            if participant:
                participants.append(participant)
        
        return participants
    
    def find_by_user_and_meeting(self, meeting_id: str, user_id: str) -> Optional[MeetingParticipant]:
        """Find a specific participant by meeting and user ID"""
        client = get_redis_client()
        
        participant_key = f"meeting:participant:{meeting_id}:{user_id}"
        data = client.hgetall(participant_key)
        
        if not data:
            return None
        
        # Parse permissions from JSON string
        try:
            permissions = json.loads(data.get("permissions", "{}"))
        except (json.JSONDecodeError, TypeError):
            permissions = {}
        
        # Parse last_accessed
        last_accessed_str = data.get("last_accessed")
        last_accessed = None
        if last_accessed_str:
            try:
                last_accessed = datetime.fromisoformat(last_accessed_str)
            except (ValueError, TypeError):
                pass
        
        return MeetingParticipant(
            user_id=data.get("user_id", user_id),
            email=data.get("email", ""),
            meeting_id=data.get("meeting_id", meeting_id),
            role=data.get("role", "viewer"),
            added_at=datetime.fromisoformat(data.get("added_at", datetime.now().isoformat())),
            added_by=data.get("added_by", ""),
            permissions=permissions,
            notifications_enabled=data.get("notifications_enabled", "True").lower() == "true",
            last_accessed=last_accessed,
        )
    
    def update_permissions(self, meeting_id: str, user_id: str, permissions: Dict[str, bool]) -> Optional[MeetingParticipant]:
        """Update participant permissions"""
        participant = self.find_by_user_and_meeting(meeting_id, user_id)
        if not participant:
            return None
        
        # Update permissions
        for perm, value in permissions.items():
            try:
                participant.update_permission(perm, value)
            except ValueError:
                # Skip invalid permissions
                continue
        
        # Save updated permissions
        client = get_redis_client()
        participant_key = f"meeting:participant:{meeting_id}:{user_id}"
        client.hset(participant_key, "permissions", json.dumps(participant.permissions))
        
        return participant
    
    def update_role(self, meeting_id: str, user_id: str, role: str) -> Optional[MeetingParticipant]:
        """Update participant role"""
        participant = self.find_by_user_and_meeting(meeting_id, user_id)
        if not participant:
            return None
        
        if role not in ["viewer", "collaborator"]:
            raise ValueError("Role must be 'viewer' or 'collaborator'")
        
        # Update role and reset permissions to defaults
        old_role = participant.role
        participant.role = role
        participant.permissions = participant._get_default_permissions()
        
        # Save updated role and permissions
        client = get_redis_client()
        participant_key = f"meeting:participant:{meeting_id}:{user_id}"
        client.hset(participant_key, mapping={
            "role": role,
            "permissions": json.dumps(participant.permissions),
        })
        
        return participant
    
    def update_last_accessed(self, meeting_id: str, user_id: str) -> bool:
        """Update the last accessed timestamp for a participant"""
        participant = self.find_by_user_and_meeting(meeting_id, user_id)
        if not participant:
            return False
        
        participant.update_last_accessed()
        
        # Save updated timestamp
        client = get_redis_client()
        participant_key = f"meeting:participant:{meeting_id}:{user_id}"
        client.hset(participant_key, "last_accessed", participant.last_accessed.isoformat())
        
        return True
    
    def count_by_meeting(self, meeting_id: str) -> int:
        """Count the number of participants for a meeting"""
        client = get_redis_client()
        
        participants_set_key = f"meeting:participants:{meeting_id}"
        return client.scard(participants_set_key)

