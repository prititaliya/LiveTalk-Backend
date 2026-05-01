"""
LiveKit Service Implementation

Implements ILiveKitService interface for LiveKit operations.
"""
import logging
import time
from typing import Dict, Any, Optional
import httpx
from domain.interfaces.livekit_service import ILiveKitService
from infrastructure.config.livekit_config import (
    get_livekit_url,
    get_livekit_api_key,
    get_livekit_api_secret
)
from livekit import api

logger = logging.getLogger(__name__)


class LiveKitService(ILiveKitService):
    """LiveKit service implementation"""
    
    def __init__(self):
        """Initialize LiveKit service with API client"""
        self._api_key = get_livekit_api_key()
        self._api_secret = get_livekit_api_secret()
        self._livekit_url = get_livekit_url()
        # Convert WebSocket URL to HTTP URL for API calls
        self._http_url = self._livekit_url.replace("ws://", "http://").replace("wss://", "https://")
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def _generate_api_token(self) -> str:
        """Generate API token for LiveKit HTTP API authentication"""
        # LiveKit API requires JWT tokens with admin grants for API operations
        token = api.AccessToken(self._api_key, self._api_secret) \
            .with_identity("api-service") \
            .with_name("API Service") \
            .with_grants(api.VideoGrants(
                room_create=True,
                room_list=True,
                room_admin=True,
                ingress_admin=True,
            ))
        return token.to_jwt()
    
    def generate_access_token(
        self,
        participant_name: str,
        room_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True
    ) -> str:
        """Generate a LiveKit access token for a participant"""
        token = api.AccessToken(self._api_key, self._api_secret) \
            .with_identity(participant_name) \
            .with_name(participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
            ))
        
        return token.to_jwt()
    
    def get_server_url(self) -> str:
        """Get the LiveKit server URL"""
        return self._livekit_url
    
    async def create_room(self, room_name: str) -> bool:
        """
        Explicitly create a LiveKit room.
        
        Args:
            room_name: Name of the room to create
            
        Returns:
            True if room was created or already exists, False otherwise
        """
        try:
            api_token = self._generate_api_token()
            response = await self._client.post(
                f"{self._http_url}/twirp/livekit.RoomService/CreateRoom",
                json={
                    "name": room_name,
                    "empty_timeout": 300,  # 5 minutes
                    "max_participants": 100
                },
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Created LiveKit room: {room_name}")
                return True
            elif response.status_code == 409:
                # Room already exists - this is fine
                logger.debug(f"Room {room_name} already exists")
                return True
            else:
                error_detail = response.text
                if response.status_code == 401:
                    error_detail = f"Authentication failed. Check API key/secret. Response: {response.text}"
                elif response.status_code == 403:
                    error_detail = f"Permission denied. Ensure API key has room_create grants. Response: {response.text}"
                logger.warning(f"Failed to create room {room_name}: {response.status_code} - {error_detail}")
                return False
        except Exception as e:
            logger.error(f"Failed to create room {room_name}: {e}", exc_info=True)
            return False
    
    async def get_ingress_status(self, ingress_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an RTMP ingress.
        
        Args:
            ingress_id: ID of the ingress to check
            
        Returns:
            Dictionary with ingress status information, or None if not found
        """
        try:
            api_token = self._generate_api_token()
            response = await self._client.post(
                f"{self._http_url}/twirp/livekit.IngressService/ListIngress",
                json={},
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                error_detail = response.text
                if response.status_code == 401:
                    error_detail = f"Authentication failed. Check API key/secret. Response: {response.text}"
                logger.warning(f"Failed to list ingresses: {response.status_code} - {error_detail}")
                return None
            
            # Check if response has content before trying to parse JSON
            if not response.text or not response.text.strip():
                logger.warning(f"Empty response from LiveKit API when listing ingresses")
                return None
            
            try:
                response_data = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}. Response text: {response.text[:200]}")
                return None
            
            ingress_list = response_data.get("items", [])
            for ingress in ingress_list:
                if ingress.get("ingress_id") == ingress_id:
                    return {
                        "ingress_id": ingress.get("ingress_id"),
                        "state": ingress.get("state", "unknown"),
                        "room_name": ingress.get("room_name"),
                        "participant_identity": ingress.get("participant_identity"),
                        "stream_key": ingress.get("stream_key"),
                        "url": ingress.get("url"),
                    }
            
            logger.debug(f"Ingress {ingress_id} not found in list of {len(ingress_list)} ingresses")
            return None
        except Exception as e:
            logger.error(f"Failed to get ingress status for {ingress_id}: {e}", exc_info=True)
            return None
    
    async def get_room_info(self, room_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a LiveKit room.
        
        Args:
            room_name: Name of the room
            
        Returns:
            Dictionary with room information, or None if not found
        """
        try:
            api_token = self._generate_api_token()
            response = await self._client.post(
                f"{self._http_url}/twirp/livekit.RoomService/ListRooms",
                json={},
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                error_detail = response.text
                if response.status_code == 401:
                    error_detail = f"Authentication failed. Check API key/secret. Response: {response.text}"
                logger.warning(f"Failed to list rooms: {response.status_code} - {error_detail}")
                return None
            
            rooms = response.json().get("rooms", [])
            for room in rooms:
                if room.get("name") == room_name:
                    return {
                        "name": room.get("name"),
                        "num_participants": room.get("num_participants", 0),
                        "creation_time": room.get("creation_time"),
                        "empty_timeout": room.get("empty_timeout"),
                    }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get room info for {room_name}: {e}", exc_info=True)
            return None
    
    async def check_agent_in_room(self, room_name: str) -> Dict[str, Any]:
        """
        Check if an agent is assigned to a room.
        
        Args:
            room_name: Name of the room to check
            
        Returns:
            Dictionary with agent status information
        """
        try:
            api_token = self._generate_api_token()
            response = await self._client.post(
                f"{self._http_url}/twirp/livekit.RoomService/ListRooms",
                json={},
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                return {
                    "agent_assigned": False,
                    "error": f"Failed to list rooms: {response.status_code}",
                    "message": "Could not check agent status"
                }
            
            rooms = response.json().get("rooms", [])
            for room in rooms:
                if room.get("name") == room_name:
                    num_participants = room.get("num_participants", 0)
                    # If there are participants, agent might be assigned
                    # We can't definitively tell if agent is assigned without listing participants
                    # But if there are participants, the agent should be triggered
                    return {
                        "agent_assigned": num_participants > 0,
                        "num_participants": num_participants,
                        "message": f"Room has {num_participants} participant(s). Agent will be assigned when participants join." if num_participants > 0 else "No participants in room. Agent not yet assigned."
                    }
            
            return {
                "agent_assigned": False,
                "message": "Room not found or no participants"
            }
        except Exception as e:
            logger.error(f"Failed to check agent in room {room_name}: {e}", exc_info=True)
            return {
                "agent_assigned": False,
                "error": str(e),
                "message": "Failed to check agent status"
            }
    
    async def create_rtmp_ingress(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        audio_only: bool = True
    ) -> Dict[str, Any]:
        """
        Create an RTMP ingress for streaming external audio/video into a LiveKit room.
        
        Args:
            room_name: Name of the LiveKit room
            participant_identity: Identity for the RTMP source participant
            participant_name: Display name for the RTMP source
            audio_only: Whether to only ingest audio (default: True)
            
        Returns:
            Dictionary containing ingress_id, rtmp_url, and stream_key
        """
        try:
            # Use LiveKit HTTP API to create ingress
            # This ensures we get the real stream_key from LiveKit
            try:
                # Prepare ingress creation request
                # Based on LiveKit API documentation: https://docs.livekit.io/transport/media/ingress-egress/ingress/transcode/
                # For RTMP input, use input_type: 0
                ingress_info = {
                    "input_type": 0,  # 0 = RTMP_INPUT, 1 = WHIP_INPUT
                    "name": f"RTMP-{room_name}",
                    "room_name": room_name,
                    "participant_identity": participant_identity,
                    "participant_name": participant_name,
                }
                
                # For audio-only RTMP, only configure audio (no video)
                # Audio configuration with preset for RTMP input
                ingress_info["audio"] = {
                    "source": "MICROPHONE",
                    "preset": "OPUS_MONO_64KBS"  # Audio preset for mono audio at 64kbps
                }
                
                # Only add video configuration if not audio-only
                if not audio_only:
                    ingress_info["video"] = {
                        "source": "CAMERA",
                        "preset": "H264_720P_30FPS_3_LAYERS"  # Video preset for 720p with 3 simulcast layers
                    }
                
                logger.info(f"Creating RTMP ingress with request:")
                logger.debug(f"  Request payload: {ingress_info}")
                
                # Ensure room exists before creating ingress
                await self.create_room(room_name)
                
                # Make HTTP request to LiveKit API
                api_token = self._generate_api_token()
                response = await self._client.post(
                    f"{self._http_url}/twirp/livekit.IngressService/CreateIngress",
                    json=ingress_info,
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    if response.status_code == 401:
                        error_detail = f"Authentication failed. Check API key/secret. Response: {response.text}"
                    elif response.status_code == 403:
                        error_detail = f"Permission denied. Ensure API key has ingress_admin grants. Response: {response.text}"
                    logger.error(f"LiveKit API error {response.status_code}: {error_detail}")
                    raise ValueError(f"LiveKit API error: {response.status_code} - {error_detail}")
                
                # Parse response - check for empty or invalid JSON
                if not response.text or not response.text.strip():
                    logger.error(f"LiveKit API returned empty response")
                    raise ValueError("LiveKit API returned empty response - cannot create ingress")
                
                try:
                    ingress_data = response.json()
                except Exception as json_error:
                    logger.error(f"Failed to parse LiveKit API response as JSON: {json_error}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response text: {response.text[:500]}")
                    raise ValueError(f"LiveKit API returned invalid JSON: {json_error}")
                
                # Log full response for debugging
                logger.info(f"LiveKit CreateIngress API response received")
                logger.info(f"Response keys: {list(ingress_data.keys())}")
                logger.debug(f"Full API response: {ingress_data}")
                
                # Extract RTMP URL and stream key from response
                # Try multiple possible field names for stream_key
                ingress_id = ingress_data.get("ingress_id", "") or ingress_data.get("ingressId", "")
                rtmp_url = ingress_data.get("url", "") or ingress_data.get("rtmp_url", "") or ingress_data.get("rtmpUrl", "")
                stream_key = ingress_data.get("stream_key", "") or ingress_data.get("streamKey", "") or ingress_data.get("rtmp_stream_key", "")
                
                logger.info(f"Extracted values (first attempt):")
                logger.info(f"  ingress_id: {ingress_id}")
                logger.info(f"  rtmp_url: {rtmp_url}")
                logger.info(f"  stream_key: {'present' if stream_key else 'MISSING'}")
                
                logger.info(f"Extracted from API response:")
                logger.info(f"  Ingress ID: {ingress_id}")
                logger.info(f"  RTMP URL: {rtmp_url}")
                logger.info(f"  Stream Key: {stream_key[:30]}..." if stream_key and len(stream_key) > 30 else f"  Stream Key: {stream_key}")
                
                # CRITICAL: Validate stream key is present and not empty
                if not stream_key or not stream_key.strip():
                    logger.warning(f"⚠️  Stream key is MISSING in CreateIngress response, attempting to query ingress...")
                    logger.warning(f"   Ingress ID: {ingress_id}")
                    logger.warning(f"   Full API response: {ingress_data}")
                    logger.warning(f"   Available fields: {list(ingress_data.keys())}")
                    
                    # Try to query the ingress to get the stream key
                    if ingress_id:
                        try:
                            logger.info(f"Querying ingress {ingress_id} to retrieve stream key...")
                            ingress_status = await self.get_ingress_status(ingress_id)
                            if ingress_status and ingress_status.get("stream_key"):
                                stream_key = ingress_status.get("stream_key")
                                logger.info(f"✅ Retrieved stream key from ingress query: {stream_key[:20]}...")
                            else:
                                logger.error(f"❌ Could not retrieve stream key from ingress query")
                                logger.error(f"   Ingress status: {ingress_status}")
                        except Exception as query_error:
                            logger.error(f"❌ Failed to query ingress for stream key: {query_error}")
                    
                    # Final check - if still no stream key, fail
                    if not stream_key or not stream_key.strip():
                        logger.error(f"❌ CRITICAL: Stream key is MISSING or EMPTY after all attempts!")
                        logger.error(f"   Cannot proceed without real stream key from LiveKit")
                        logger.error(f"   This ingress will NOT work with RTMP streaming")
                        raise ValueError("LiveKit API did not return a stream_key and could not retrieve it from ingress. Cannot proceed without real stream key from LiveKit.")
                
                # CRITICAL: Validate stream key is NOT our generated pattern
                if stream_key.startswith(f"{room_name}-") and participant_identity in stream_key:
                    logger.error(f"❌ CRITICAL: Stream key appears to be GENERATED, not from LiveKit!")
                    logger.error(f"   Stream key: {stream_key}")
                    logger.error(f"   Room name: {room_name}")
                    logger.error(f"   This key will NOT work with RTMP streaming")
                    logger.error(f"   Full API response: {ingress_data}")
                    raise ValueError(f"LiveKit API returned an invalid stream key that appears to be generated. Expected random alphanumeric string from LiveKit, got: {stream_key}")
                
                # Validate stream key looks like a real LiveKit key
                # Real LiveKit keys are typically random alphanumeric strings
                # They should NOT contain the room name or participant identity
                if len(stream_key) < 10:
                    logger.warning(f"⚠️  Stream key is very short ({len(stream_key)} chars) - may be invalid")
                
                logger.info(f"✅ Stream key validation passed:")
                logger.info(f"   - Key is present: ✅")
                logger.info(f"   - Key is not empty: ✅")
                logger.info(f"   - Key does not match generated pattern: ✅")
                logger.info(f"   - Key length: {len(stream_key)} characters")
                
                # Fix RTMP URL if it's using rtmp:// instead of rtmps:// for LiveKit Cloud
                if rtmp_url and ".livekit.cloud" in rtmp_url.lower():
                    if rtmp_url.startswith("rtmp://"):
                        logger.warning(f"LiveKit API returned rtmp:// for LiveKit Cloud, fixing to rtmps://")
                        rtmp_url = rtmp_url.replace("rtmp://", "rtmps://", 1)
                
                # Validate that we got the required fields
                if not rtmp_url:
                    logger.error(f"RTMP URL is empty in LiveKit response. Full response: {ingress_data}")
                    raise ValueError("LiveKit API returned empty RTMP URL")
                
                if not ingress_id:
                    logger.error(f"Ingress ID is empty in LiveKit response. Full response: {ingress_data}")
                    raise ValueError("LiveKit API returned empty ingress_id")
                
                logger.info(f"✅ Successfully created RTMP ingress {ingress_id} for room {room_name}")
                logger.info(f"✅ RTMP URL: {rtmp_url}")
                logger.info(f"✅ Stream Key (from LiveKit): {stream_key[:20]}..." if len(stream_key) > 20 else f"✅ Stream Key (from LiveKit): {stream_key}")
                
                # Validate RTMP URL format for LiveKit Cloud
                if ".livekit.cloud" in rtmp_url.lower() and not rtmp_url.startswith("rtmps://"):
                    logger.error(f"Invalid RTMP URL for LiveKit Cloud: {rtmp_url}. Must use rtmps://")
                    raise ValueError(f"LiveKit Cloud requires rtmps:// protocol, got: {rtmp_url}")
                
                return {
                    "ingress_id": ingress_id,
                    "rtmp_url": rtmp_url,
                    "stream_key": stream_key,
                    "room_name": room_name,
                    "participant_identity": participant_identity
                }
            except Exception as api_error:
                # CRITICAL: Never use fallback - stream keys MUST come from LiveKit API
                # If API call fails, we cannot proceed without a real stream key
                logger.error(f"❌ CRITICAL: Failed to create RTMP ingress via LiveKit API: {api_error}")
                logger.error(f"   Stream keys MUST come from LiveKit API - cannot use fallback")
                logger.error(f"   Full error details:", exc_info=True)
                
                # Log the request that failed for debugging
                logger.error(f"   Failed request payload: {ingress_info}")
                logger.error(f"   API endpoint: {self._http_url}/twirp/livekit.IngressService/CreateIngress")
                
                raise ValueError(f"Failed to create RTMP ingress via LiveKit API: {api_error}. Stream keys must come from LiveKit - cannot proceed without real stream key.")
        except Exception as e:
            logger.error(f"Failed to create RTMP ingress: {e}", exc_info=True)
            raise ValueError(f"Failed to create RTMP ingress: {str(e)}")
    
    async def delete_rtmp_ingress(self, ingress_id: str) -> bool:
        """
        Delete an RTMP ingress session.
        
        Args:
            ingress_id: ID of the ingress to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            api_token = self._generate_api_token()
            response = await self._client.post(
                f"{self._http_url}/twirp/livekit.IngressService/DeleteIngress",
                json={"ingress_id": ingress_id},
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Deleted RTMP ingress {ingress_id}")
                return True
            else:
                error_detail = response.text
                if response.status_code == 401:
                    error_detail = f"Authentication failed. Check API key/secret. Response: {response.text}"
                elif response.status_code == 403:
                    error_detail = f"Permission denied. Ensure API key has ingress_admin grants. Response: {response.text}"
                logger.warning(f"Failed to delete RTMP ingress {ingress_id}: {response.status_code} - {error_detail}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete RTMP ingress {ingress_id}: {e}", exc_info=True)
            return False
    
    async def start_recording_remote(
        self,
        room_name: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Start recording remotely (for mobile control).
        This triggers the same LiveKit room connection and RTMP ingress creation.
        
        Args:
            room_name: Name of the LiveKit room
            user_id: User ID starting the recording
            
        Returns:
            Dictionary containing ingress_id, rtmp_url, and stream_key
        """
        # Use the same RTMP ingress creation as regular recording
        participant_identity = f"rtmp-{user_id}"
        participant_name = f"RTMP-{room_name}"
        
        return await self.create_rtmp_ingress(
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=participant_name,
            audio_only=True
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

