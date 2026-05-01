"""
Redis Transcript Repository Implementation

Implements ITranscriptRepository interface using Redis as the storage backend.
"""
import json
from datetime import datetime
from typing import List, Optional

from domain.interfaces.transcript_repository import ITranscriptRepository
from domain.entities.meeting import Meeting
from domain.entities.transcript import Transcript
from domain.value_objects.meeting_id import MeetingId
from infrastructure.config.redis_config import get_redis_client


class RedisTranscriptRepository(ITranscriptRepository):
    """Redis implementation of transcript repository"""
    
    def save(self, meeting: Meeting) -> MeetingId:
        """Save a meeting with its transcripts to Redis"""
        client = get_redis_client()
        
        # Use existing meeting_id or generate new one
        if isinstance(meeting.meeting_id, MeetingId):
            meeting_id = meeting.meeting_id
        else:
            meeting_id = MeetingId(meeting.meeting_id)
        
        redis_key = f"transcript:{meeting_id.value}"
        
        # Convert transcripts to JSON string
        transcripts_json = json.dumps([
            {
                "speaker": t.speaker,
                "text": t.text,
                "timestamp": t.timestamp.isoformat(),
                "is_final": t.is_final
            }
            for t in meeting.transcripts
        ])
        
        # Prepare hash data
        hash_data = {
            "meeting_id": meeting_id.value,
            "meeting_name": meeting.meeting_name,
            "room_name": meeting.room_name,
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat() if meeting.end_time else datetime.now().isoformat(),
            "transcripts": transcripts_json,
            "total_entries": str(meeting.total_entries),
            "created_at": meeting.created_at.isoformat() if meeting.created_at else datetime.now().isoformat(),
        }
        
        # Add user_id if present
        if hasattr(meeting, 'user_id') and meeting.user_id:
            hash_data["user_id"] = meeting.user_id
        
        # Store in Redis
        client.hset(redis_key, mapping=hash_data)
        
        # Add to indexes
        self._add_to_indexes(client, meeting_id.value, hash_data)
        
        # Add to user index if user_id is present
        if hasattr(meeting, 'user_id') and meeting.user_id:
            client.sadd(f"transcripts:by_user:{meeting.user_id}", meeting_id.value)
        
        return meeting_id
    
    def get_by_id(self, meeting_id: MeetingId) -> Optional[Meeting]:
        """Retrieve a meeting by its ID from Redis"""
        client = get_redis_client()
        redis_key = f"transcript:{meeting_id.value}"
        
        # Get all hash fields
        data = client.hgetall(redis_key)
        
        if not data:
            return None
        
        # Parse transcripts from JSON string
        try:
            transcripts_data = json.loads(data.get("transcripts", "[]"))
            transcripts = [
                Transcript(
                    speaker=t["speaker"],
                    text=t["text"],
                    timestamp=datetime.fromisoformat(t["timestamp"]),
                    is_final=t.get("is_final", True)
                )
                for t in transcripts_data
            ]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            transcripts = []
        
        # Reconstruct meeting entity
        return Meeting(
            meeting_id=meeting_id.value,
            meeting_name=data.get("meeting_name", ""),
            room_name=data.get("room_name", ""),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.now().isoformat())),
            transcripts=transcripts,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            user_id=data.get("user_id"),  # Optional user_id
        )
    
    def search(
        self,
        meeting_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Meeting]:
        """Search for meetings by various criteria"""
        client = get_redis_client()
        meeting_ids = set()
        
        # Search by meeting name
        if meeting_name:
            safe_name = "".join(
                c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
            ).strip().replace(" ", "_").lower()
            name_key = f"transcripts:by_name:{safe_name}"
            ids = client.smembers(name_key)
            if meeting_ids:
                meeting_ids = meeting_ids.intersection(ids)
            else:
                meeting_ids = ids
        
        # Search by date range
        if date_from or date_to:
            date_ids = set()
            
            if date_from and date_to:
                current = date_from
                while current <= date_to:
                    date_key = current.strftime("%Y-%m-%d")
                    ids = client.smembers(f"transcripts:by_date:{date_key}")
                    date_ids.update(ids)
                    # Move to next day
                    from datetime import timedelta
                    current = current + timedelta(days=1)
            elif date_from:
                date_key = date_from.strftime("%Y-%m-%d")
                ids = client.smembers(f"transcripts:by_date:{date_key}")
                date_ids.update(ids)
            elif date_to:
                date_key = date_to.strftime("%Y-%m-%d")
                ids = client.smembers(f"transcripts:by_date:{date_key}")
                date_ids.update(ids)
            
            if meeting_ids:
                meeting_ids = meeting_ids.intersection(date_ids)
            else:
                meeting_ids = date_ids
        
        # If no filters, get all transcripts
        if not meeting_ids:
            meeting_ids = client.smembers("transcripts:all")
        
        # Retrieve meetings
        results = []
        for meeting_id_str in list(meeting_ids)[:limit]:
            meeting_id = MeetingId(meeting_id_str)
            meeting = self.get_by_id(meeting_id)
            if meeting:
                results.append(meeting)
        
        # Sort by start_time (most recent first)
        results.sort(key=lambda x: x.start_time, reverse=True)
        
        return results
    
    def delete(self, meeting_id: MeetingId) -> bool:
        """Delete a meeting by its ID from Redis"""
        client = get_redis_client()
        redis_key = f"transcript:{meeting_id.value}"
        
        # Get meeting data to find indexes
        data = client.hgetall(redis_key)
        if not data:
            return False
        
        # Remove from indexes
        client.srem("transcripts:all", meeting_id.value)
        
        # Remove from date index
        start_time = data.get("start_time", datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            date_key = dt.strftime("%Y-%m-%d")
            client.srem(f"transcripts:by_date:{date_key}", meeting_id.value)
        except:
            pass
        
        # Remove from name index
        meeting_name = data.get("meeting_name", "")
        if meeting_name:
            safe_name = "".join(
                c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
            ).strip().replace(" ", "_").lower()
            client.srem(f"transcripts:by_name:{safe_name}", meeting_id.value)
        
        # Delete the hash
        client.delete(redis_key)
        
        return True
    
    def _add_to_indexes(self, client, meeting_id: str, hash_data: dict):
        """Add meeting_id to various indexes for searching"""
        # Add to all transcripts index
        client.sadd("transcripts:all", meeting_id)
        
        # Add to date index
        start_time = hash_data.get("start_time", datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            date_key = dt.strftime("%Y-%m-%d")
            client.sadd(f"transcripts:by_date:{date_key}", meeting_id)
        except:
            date_key = datetime.now().strftime("%Y-%m-%d")
            client.sadd(f"transcripts:by_date:{date_key}", meeting_id)
        
        # Add to meeting name index
        meeting_name = hash_data.get("meeting_name", "")
        if meeting_name:
            safe_name = "".join(
                c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
            ).strip().replace(" ", "_").lower()
            client.sadd(f"transcripts:by_name:{safe_name}", meeting_id)
        
        # Add to user index if user_id is present
        user_id = hash_data.get("user_id")
        if user_id:
            client.sadd(f"transcripts:by_user:{user_id}", meeting_id)

