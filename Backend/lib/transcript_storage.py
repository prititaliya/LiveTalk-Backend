import json
import logging
import redis
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)


def generate_meeting_id(room_name: str, timestamp: Optional[str] = None) -> str:
    """
    Generate a unique meeting ID from room name and timestamp.
    Format: {room_name}_{timestamp} or {room_name}_{current_timestamp}
    """
    if timestamp:
        # Extract date part from timestamp if it's ISO format
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
        except:
            timestamp_str = timestamp
    else:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean room name for use in key
    safe_room_name = "".join(
        c for c in room_name if c.isalnum() or c in ("-", "_")
    ).strip().replace(" ", "_")
    
    return f"{safe_room_name}_{timestamp_str}"


def store_transcript(room_name: str, transcript_data: Dict, user_id: str = None) -> str:
    """
    Store transcript data in Redis as a Hash.
    
    Args:
        room_name: The room name used for the recording
        transcript_data: Dictionary containing transcript data from JSON file
        
    Returns:
        meeting_id: The unique meeting ID used as the Redis key
        
    Raises:
        redis.RedisError: If Redis operation fails
        ValueError: If transcript_data is invalid
    """
    client = get_redis_client()
    
    # Generate meeting ID
    start_time = transcript_data.get("start_time")
    meeting_id = generate_meeting_id(room_name, start_time)
    
    # Prepare data for Redis Hash
    redis_key = f"transcript:{meeting_id}"
    
    # Extract live participants from transcripts (unique speakers)
    transcripts_list = transcript_data.get("transcripts", [])
    live_participants = list(set([t.get("speaker", "") for t in transcripts_list if t.get("speaker")]))
    
    # Store transcript data as Hash fields
    hash_data = {
        "meeting_id": meeting_id,
        "meeting_name": transcript_data.get("meeting_name", room_name),
        "room_name": room_name,
        "start_time": transcript_data.get("start_time", datetime.now().isoformat()),
        "end_time": transcript_data.get("last_updated", datetime.now().isoformat()),
        "transcripts": json.dumps(transcripts_list),  # Store as JSON string
        "total_entries": str(transcript_data.get("total_entries", 0)),
        "created_at": datetime.now().isoformat(),
        "participant_count": "0",  # Initialize participant count
        "live_participants": json.dumps(live_participants),  # Store live participants as JSON array
    }
    
    # Add user_id if provided
    if user_id:
        hash_data["user_id"] = user_id
    
    # Store in Redis Hash
    client.hset(redis_key, mapping=hash_data)
    
    # Set TTL (optional: 1 year = 31536000 seconds)
    # Uncomment if you want automatic expiration:
    # client.expire(redis_key, 31536000)
    
    # Add to indexes
    _add_to_indexes(client, meeting_id, hash_data)
    
    # Add to user index if user_id is provided
    if user_id:
        client.sadd(f"transcripts:by_user:{user_id}", meeting_id)
    
    logger.info(f"Stored transcript in Redis: {redis_key}")
    return meeting_id


def _add_to_indexes(client: redis.Redis, meeting_id: str, hash_data: Dict):
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
        # Fallback to today's date if parsing fails
        date_key = datetime.now().strftime("%Y-%m-%d")
        client.sadd(f"transcripts:by_date:{date_key}", meeting_id)
    
    # Add to meeting name index
    meeting_name = hash_data.get("meeting_name", "")
    if meeting_name:
        safe_name = "".join(
            c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
        ).strip().replace(" ", "_").lower()
        client.sadd(f"transcripts:by_name:{safe_name}", meeting_id)


def get_transcript(meeting_id: str) -> Optional[Dict]:
    """
    Retrieve a transcript by meeting ID.
    
    Args:
        meeting_id: The meeting ID to retrieve
        
    Returns:
        Dictionary containing transcript data, or None if not found
    """
    client = get_redis_client()
    redis_key = f"transcript:{meeting_id}"
    
    # Get all hash fields
    data = client.hgetall(redis_key)
    
    if not data:
        return None
    
    # Parse transcripts JSON string back to list
    try:
        transcripts = json.loads(data.get("transcripts", "[]"))
    except:
        transcripts = []
    
    # Reconstruct transcript data
    # Ensure all string values are properly decoded (Redis with decode_responses=True should already return strings)
    user_id = data.get("user_id")
    if user_id is not None:
        user_id = str(user_id).strip() if isinstance(user_id, (str, bytes)) else None
    
    # Parse live participants from JSON string
    live_participants = []
    try:
        live_participants_str = data.get("live_participants", "[]")
        if live_participants_str:
            live_participants = json.loads(live_participants_str)
    except (json.JSONDecodeError, TypeError):
        pass
    
    return {
        "meeting_id": str(data.get("meeting_id", "")) if data.get("meeting_id") else "",
        "meeting_name": str(data.get("meeting_name", "")) if data.get("meeting_name") else "",
        "room_name": str(data.get("room_name", "")) if data.get("room_name") else "",
        "start_time": str(data.get("start_time", "")) if data.get("start_time") else "",
        "end_time": str(data.get("end_time", "")) if data.get("end_time") else None,
        "transcripts": transcripts,
        "total_entries": int(data.get("total_entries", 0)),
        "created_at": str(data.get("created_at", "")) if data.get("created_at") else "",
        "user_id": user_id,  # Include user_id in response
        "participant_count": int(data.get("participant_count", 0)),
        "live_participants": live_participants,
    }


def search_transcripts(
    meeting_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Search transcripts by various criteria.
    
    Args:
        meeting_name: Filter by meeting name (partial match)
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        limit: Maximum number of results to return
        
    Returns:
        List of transcript dictionaries matching the criteria
    """
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
            # Get all dates in range
            from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            current = from_dt
            while current <= to_dt:
                date_key = current.strftime("%Y-%m-%d")
                ids = client.smembers(f"transcripts:by_date:{date_key}")
                date_ids.update(ids)
                current = datetime(current.year, current.month, current.day + 1)
        elif date_from:
            date_key = date_from
            ids = client.smembers(f"transcripts:by_date:{date_key}")
            date_ids.update(ids)
        elif date_to:
            date_key = date_to
            ids = client.smembers(f"transcripts:by_date:{date_key}")
            date_ids.update(ids)
        
        if meeting_ids:
            meeting_ids = meeting_ids.intersection(date_ids)
        else:
            meeting_ids = date_ids
    
    # If no filters, get all transcripts
    if not meeting_ids:
        meeting_ids = client.smembers("transcripts:all")
    
    # Retrieve transcript data for each meeting_id
    results = []
    for meeting_id in list(meeting_ids)[:limit]:
        transcript = get_transcript(meeting_id)
        if transcript:
            results.append(transcript)
    
    # Sort by start_time (most recent first)
    results.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    
    return results


def get_transcripts_by_user_id(user_id: str) -> List[Dict]:
    """
    Retrieve all transcripts for a specific user.
    
    Args:
        user_id: The user ID to retrieve transcripts for
        
    Returns:
        List of transcript dictionaries belonging to the user, sorted by most recent first
    """
    client = get_redis_client()
    
    # Get all meeting IDs for this user from the user index
    user_index_key = f"transcripts:by_user:{user_id}"
    meeting_ids = client.smembers(user_index_key)
    
    if not meeting_ids:
        logger.info(f"No transcripts found for user: {user_id}")
        return []
    
    # Retrieve transcript data for each meeting_id
    results = []
    for meeting_id in meeting_ids:
        transcript = get_transcript(meeting_id)
        if transcript:
            # Verify the transcript belongs to this user (safety check)
            # Note: user_id is stored in the transcript hash, but we already filtered by index
            results.append(transcript)
    
    # Sort by start_time (most recent first)
    results.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    
    logger.info(f"Retrieved {len(results)} transcripts for user: {user_id}")
    return results


def update_transcript(meeting_id: str, meeting_name: Optional[str] = None, transcripts: Optional[List[Dict]] = None) -> Optional[Dict]:
    """
    Update transcript data in Redis.
    
    Args:
        meeting_id: The meeting ID to update
        meeting_name: Optional new meeting name
        transcripts: Optional new transcripts list
        
    Returns:
        Updated transcript dictionary, or None if not found
        
    Raises:
        ValueError: If transcript is not found
    """
    client = get_redis_client()
    redis_key = f"transcript:{meeting_id}"
    
    # Get existing transcript
    existing_data = client.hgetall(redis_key)
    if not existing_data:
        return None
    
    # Update meeting name if provided
    if meeting_name is not None:
        old_name = existing_data.get("meeting_name", "")
        # Remove from old name index
        if old_name:
            old_safe_name = "".join(
                c for c in old_name if c.isalnum() or c in ("-", "_", " ")
            ).strip().replace(" ", "_").lower()
            client.srem(f"transcripts:by_name:{old_safe_name}", meeting_id)
        
        # Update meeting name
        client.hset(redis_key, "meeting_name", meeting_name)
        
        # Add to new name index
        new_safe_name = "".join(
            c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
        ).strip().replace(" ", "_").lower()
        client.sadd(f"transcripts:by_name:{new_safe_name}", meeting_id)
    
    # Update transcripts if provided
    if transcripts is not None:
        # Update transcripts JSON string
        client.hset(redis_key, "transcripts", json.dumps(transcripts))
        # Update total_entries
        client.hset(redis_key, "total_entries", str(len(transcripts)))
    
    logger.info(f"Updated transcript in Redis: {redis_key}")
    
    # Return updated transcript
    return get_transcript(meeting_id)


def rename_speaker_in_transcript(meeting_id: str, old_speaker: str, new_speaker: str) -> Optional[Dict]:
    """
    Rename a speaker across all entries in a transcript.
    
    Args:
        meeting_id: The meeting ID
        old_speaker: The current speaker name/ID
        new_speaker: The new speaker name/ID
        
    Returns:
        Updated transcript dictionary, or None if not found
        
    Raises:
        ValueError: If transcript is not found or old_speaker doesn't exist
    """
    client = get_redis_client()
    redis_key = f"transcript:{meeting_id}"
    
    # Get existing transcript
    existing_data = client.hgetall(redis_key)
    if not existing_data:
        return None
    
    # Parse transcripts
    try:
        transcripts = json.loads(existing_data.get("transcripts", "[]"))
    except:
        transcripts = []
    
    if not transcripts:
        logger.warning(f"No transcripts found for meeting: {meeting_id}")
        return get_transcript(meeting_id)
    
    # Update all occurrences of old_speaker to new_speaker
    updated_count = 0
    for entry in transcripts:
        if entry.get("speaker") == old_speaker:
            entry["speaker"] = new_speaker
            updated_count += 1
    
    if updated_count == 0:
        logger.warning(f"Speaker '{old_speaker}' not found in transcript: {meeting_id}")
        return get_transcript(meeting_id)
    
    # Save updated transcripts
    client.hset(redis_key, "transcripts", json.dumps(transcripts))
    
    logger.info(f"Renamed speaker '{old_speaker}' to '{new_speaker}' in {updated_count} entries for transcript: {meeting_id}")
    
    # Return updated transcript
    return get_transcript(meeting_id)


def delete_transcript(meeting_id: str) -> bool:
    """
    Delete a transcript from Redis and remove from indexes.
    
    Args:
        meeting_id: The meeting ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    client = get_redis_client()
    redis_key = f"transcript:{meeting_id}"
    
    # Get transcript to find indexes
    data = client.hgetall(redis_key)
    if not data:
        return False
    
    # Get user_id before deleting to remove from user index
    user_id = data.get("user_id")
    if user_id is not None:
        user_id = str(user_id).strip() if isinstance(user_id, (str, bytes)) else None
    
    logger.info(f"Deleting transcript {meeting_id}, user_id: {user_id}")
    
    # Remove from indexes
    client.srem("transcripts:all", meeting_id)
    
    # Remove from date index
    start_time = data.get("start_time", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date_key = dt.strftime("%Y-%m-%d")
        client.srem(f"transcripts:by_date:{date_key}", meeting_id)
    except:
        pass
    
    # Remove from name index
    meeting_name = data.get("meeting_name", "")
    if meeting_name:
        safe_name = "".join(
            c for c in meeting_name if c.isalnum() or c in ("-", "_", " ")
        ).strip().replace(" ", "_").lower()
        client.srem(f"transcripts:by_name:{safe_name}", meeting_id)
    
    # Remove from user index if user_id exists
    if user_id:
        removed_from_user_index = client.srem(f"transcripts:by_user:{user_id}", meeting_id)
        logger.info(f"Removed from user index: {removed_from_user_index} items removed")
    
    # Delete participant data (if any exists) - do this before deleting the hash
    participants_set_key = f"meeting:participants:{meeting_id}"
    user_ids = client.smembers(participants_set_key)
    for participant_user_id in user_ids:
        participant_key = f"meeting:participant:{meeting_id}:{participant_user_id}"
        client.delete(participant_key)
    client.delete(participants_set_key)
    
    # Delete the hash
    deleted_count = client.delete(redis_key)
    logger.info(f"Deleted transcript hash: {redis_key}, deleted: {deleted_count}")
    
    # Verify deletion
    verify_data = client.hgetall(redis_key)
    if verify_data:
        logger.error(f"WARNING: Transcript {meeting_id} still exists after deletion!")
        return False
    
    logger.info(f"Successfully deleted transcript from Redis: {redis_key}")
    return True


def get_meeting_participant_count(meeting_id: str) -> int:
    """
    Get the number of post-meeting participants for a meeting.
    
    Args:
        meeting_id: The meeting ID
        
    Returns:
        Number of participants
    """
    from infrastructure.repositories.redis_meeting_participant_repository import RedisMeetingParticipantRepository
    repository = RedisMeetingParticipantRepository()
    return repository.count_by_meeting(meeting_id)


def update_meeting_participant_count(meeting_id: str):
    """
    Update the participant count in the meeting hash.
    
    Args:
        meeting_id: The meeting ID
    """
    client = get_redis_client()
    meeting_key = f"transcript:{meeting_id}"
    
    # Get current count from repository
    count = get_meeting_participant_count(meeting_id)
    
    # Update count in meeting hash
    client.hset(meeting_key, "participant_count", str(count))

