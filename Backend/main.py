import os
import json
import logging
import time
import asyncio
from collections.abc import AsyncIterable
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from livekit import rtc, agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ModelSettings
from livekit.agents import stt
from livekit.plugins import noise_cancellation, silero

load_dotenv(".env.local")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diarizer")

try:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
    TURN_DETECTOR_AVAILABLE = True
except (ImportError, Exception) as e:
    logger.warning(f"Turn detector not available (PyTorch may be missing): {e}")
    MultilingualModel = None
    TURN_DETECTOR_AVAILABLE = False

try:
    from sounddevice import PortAudioError
except ImportError:
    PortAudioError = None


speaker_label_map: Dict[str, str] = {}
next_speaker_num: int = 1

# Global agent registry: room_name -> agent instance
# This allows remote control to access agents and call stop_recording
_active_agents: Dict[str, 'DiarizationAgent'] = {}

# Transcripts directory
TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

def label_for_speaker_id(speaker_id: Optional[str]) -> str:
    """Generate a label for a speaker ID"""
    global next_speaker_num
    if not speaker_id:
        speaker_id = "unknown"
    if speaker_id not in speaker_label_map:
        speaker_label_map[speaker_id] = f"Speaker {next_speaker_num}"
        next_speaker_num += 1
    return speaker_label_map[speaker_id]


class DiarizationAgent(Agent):
    def __init__(self, ctx: agents.JobContext) -> None:
        super().__init__(
            instructions=(
                "You are a silent transcription agent. "
                "Do not respond or speak; only transcribe user speech with speaker labels."
            )
        )
        self.ctx = ctx
        self.json_file_path = None
        # Track speaker changes for better diarization
        self.recent_speaker_ids = []
        self.last_speaker_id = None
        # For manual diarization: track speaker counter and turn changes
        self._manual_speaker_counter = 1
        self._last_speaker_time = None
        self._turn_detected = False
        # Recording state management
        self.recording_state: str = "idle"  # 'idle', 'recording', 'paused', 'stopped'
        self.remote_session_id: Optional[str] = None
        self._should_disconnect: bool = False  # Flag to trigger room disconnect
        # Transcript buffering for reliability
        self._transcript_buffer: List[Dict] = []
        self._last_flush_time = time.time()
        self._flush_interval = 30  # Flush buffer every 30 seconds
        # Initialize recording state service if available
        try:
            from core.dependency_injection import setup_dependencies
            container = setup_dependencies()
            self.recording_state_service = container.recording_state_service()
        except Exception as e:
            logger.warning(f"Could not initialize recording state service: {e}")
            self.recording_state_service = None

    def _get_json_file_path(self) -> Path:
        """Get or create the JSON file path for this session"""
        if self.json_file_path is None:
            room_name = self.ctx.room.name if self.ctx.room else "Meeting"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(
                c for c in room_name if c.isalnum() or c in ("-", "_", " ")
            ).strip().replace(" ", "_")
            filename = f"{safe_name}_{timestamp}.json"
            self.json_file_path = TRANSCRIPTS_DIR / filename
            
            # Check if a file for this room already exists (to avoid duplicates on agent restart)
            # Look for existing files with the same room name from today
            today_prefix = datetime.now().strftime("%Y%m%d")
            existing_files = list(TRANSCRIPTS_DIR.glob(f"{safe_name}_{today_prefix}_*.json"))
            if existing_files:
                # Use the most recent file for this room from today
                existing_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                most_recent = existing_files[0]
                # Only reuse if it was created in the last 5 minutes (likely same session)
                file_age = datetime.now().timestamp() - most_recent.stat().st_mtime
                if file_age < 300:  # 5 minutes
                    self.json_file_path = most_recent
                    return self.json_file_path
            
            # Initialize JSON file if it doesn't exist
            if not self.json_file_path.exists():
                initial_data = {
                    "meeting_name": room_name,
                    "start_time": datetime.now().isoformat(),
                    "transcripts": []
                }
                with open(self.json_file_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
                # Create status file to notify frontend that agent has started
                self._create_agent_status_file(room_name, "started")
        
        return self.json_file_path

    def _create_agent_status_file(self, room_name: str, status: str):
        """Create a status file to notify frontend of agent status"""
        try:
            status_file = TRANSCRIPTS_DIR / f"{room_name}_agent_status.json"
            status_data = {
                "room_name": room_name,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to create agent status file: {e}")

    def _append_to_json(self, speaker: str, text: str, timestamp: str, retry_count: int = 3):
        """Append a transcript entry to the JSON file with retry logic"""
        transcript_entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
            "is_final": True
        }
        
        # Attempt to write with retry logic
        for attempt in range(retry_count):
            try:
                file_path = self._get_json_file_path()
                
                # Read existing data
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Append new transcript
                data["transcripts"].append(transcript_entry)
                data["total_entries"] = len(data["transcripts"])
                data["last_updated"] = datetime.now().isoformat()
                
                # Write back to file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Success - return immediately
                return True
                
            except Exception as e:
                if attempt < retry_count - 1:
                    # Exponential backoff: wait 0.1s, 0.2s, 0.4s
                    wait_time = 0.1 * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    # Final attempt failed - add to buffer for later flush
                    logger.error(f"Failed to append to JSON file after {retry_count} attempts: {e}")
                    self._transcript_buffer.append(transcript_entry)
                    return False
        
        return False
    
    def _flush_transcript_buffer(self):
        """Flush any buffered transcripts to file"""
        if not self._transcript_buffer:
            return
        
        try:
            file_path = self._get_json_file_path()
            
            # Read existing data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Get existing transcript keys for deduplication
            existing_keys = {(e.get("speaker"), e.get("text"), e.get("timestamp")) 
                           for e in data.get("transcripts", [])}
            
            # Append only new buffered transcripts
            new_entries = []
            for entry in self._transcript_buffer:
                entry_key = (entry.get("speaker"), entry.get("text"), entry.get("timestamp"))
                if entry_key not in existing_keys:
                    data["transcripts"].append(entry)
                    new_entries.append(entry)
                    existing_keys.add(entry_key)
            
            if new_entries:
                data["total_entries"] = len(data["transcripts"])
                data["last_updated"] = datetime.now().isoformat()
                
                # Write back to file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Clear buffer on successful write
            self._transcript_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush transcript buffer: {e}")
            # Buffer will be retried on next flush

    def stt_node(self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings) -> AsyncIterable[stt.SpeechEvent | str]:
        async def _transcribe():
            try:
                if not self.ctx.room or len(list(self.ctx.room.remote_participants.values())) == 0:
                    logger.warning("No participants in room - waiting for RTMP stream to connect")
                
                # Determine if we need manual diarization
                stt_model = os.environ.get("STT_MODEL", "speechmatics").lower()
                needs_manual_diarization = stt_model in ["deepgram", "assemblyai"]
                
                # Track if we've received any speech events
                speech_event_count = 0
                first_speech_logged = False
                
                # Access turn detection from the session if available
                turn_detector = getattr(self, '_turn_detector', None)
                
                # Initialize manual diarization state
                if needs_manual_diarization:
                    self._manual_speaker_counter = 1
                    self._last_speaker_time = None
                    self._turn_detected = False
                    current_speaker_id = f"speaker_{self._manual_speaker_counter}"
                
                async for ev in Agent.default.stt_node(self, audio, model_settings):
                    if isinstance(ev, stt.SpeechEvent):
                        # Periodic buffer flush (every 30 seconds or 100 events)
                        current_time = time.time()
                        if current_time - self._last_flush_time > self._flush_interval or speech_event_count % 100 == 0:
                            self._flush_transcript_buffer()
                            self._last_flush_time = current_time
                        
                        # Check recording state - skip processing if paused or stopped
                        if self.recording_state == "paused":
                            continue
                        elif self.recording_state == "stopped":
                            # Flush buffer before stopping
                            self._flush_transcript_buffer()
                            self._should_disconnect = True
                            if self.ctx.room:
                                try:
                                    await self.ctx.room.disconnect()
                                except Exception as e:
                                    logger.error(f"Error disconnecting from room: {e}")
                            break
                        
                        # Periodically check Redis state for remote control commands
                        if speech_event_count % 50 == 0 and self.recording_state_service and self.remote_session_id:
                            try:
                                redis_state = self.recording_state_service.get_agent_state(self.remote_session_id)
                                if redis_state and redis_state != self.recording_state:
                                    if redis_state == "stopped":
                                        self.stop_recording()
                                    elif redis_state == "paused":
                                        self.pause_recording()
                                    elif redis_state == "recording":
                                        self.resume_recording()
                            except Exception:
                                pass  # Silently handle Redis errors
                        elif self.recording_state == "idle":
                            if not first_speech_logged:
                                self.start_recording()
                        
                        speech_event_count += 1
                        first_speech_logged = True
                        
                        try:
                            if ev.alternatives:
                                alt = ev.alternatives[0]
                                text = alt.text or ""
                                
                                # Get speaker information from STT event
                                speaker_id_attr = getattr(alt, "speaker_id", None)
                                speaker_attr = getattr(alt, "speaker", None)
                                speaker_label_attr = getattr(alt, "speaker_label", None)
                                
                                alt_dict = None
                                if hasattr(alt, "__dict__"):
                                    alt_dict = alt.__dict__
                                elif isinstance(alt, dict):
                                    alt_dict = alt
                                
                                ev_speaker = getattr(ev, "speaker", None) or getattr(ev, "speaker_id", None)
                                
                                # Comprehensive speaker extraction
                                spk = None
                                if speaker_id_attr:
                                    spk = str(speaker_id_attr)
                                elif speaker_attr:
                                    spk = str(speaker_attr)
                                elif speaker_label_attr:
                                    spk = str(speaker_label_attr)
                                elif ev_speaker:
                                    spk = str(ev_speaker)
                                elif alt_dict:
                                    spk = (alt_dict.get("speaker_id") or 
                                           alt_dict.get("speaker") or 
                                           alt_dict.get("speaker_label") or
                                           alt_dict.get("speaker_name"))
                                    if spk:
                                        spk = str(spk)
                                
                                # For models without native diarization, implement manual speaker detection
                                if needs_manual_diarization:
                                    ev_type = getattr(ev, "type", None)
                                    ev_type_name = getattr(ev_type, "name", str(ev_type)) if ev_type else None
                                    
                                    current_time = datetime.now()
                                    
                                    if self._last_speaker_time is not None:
                                        time_since_last = (current_time - self._last_speaker_time).total_seconds()
                                        
                                        if time_since_last > 1.5:
                                            if len(set(self.recent_speaker_ids[-5:])) > 1 or self._turn_detected:
                                                self._manual_speaker_counter += 1
                                                self._turn_detected = False
                                    
                                    spk = f"speaker_{self._manual_speaker_counter}"
                                    self._last_speaker_time = current_time
                                    
                                    if self._turn_detected:
                                        self._turn_detected = False
                                
                                if not spk:
                                    if not needs_manual_diarization:
                                        logger.warning(f"No speaker ID found in STT event")
                                    spk = "speaker_1"
                                
                                if not needs_manual_diarization:
                                    self.recent_speaker_ids.append(spk)
                                    if len(self.recent_speaker_ids) > 50:
                                        self.recent_speaker_ids.pop(0)
                                    self.last_speaker_id = spk
                                else:
                                    self.recent_speaker_ids.append(spk)
                                    if len(self.recent_speaker_ids) > 20:
                                        self.recent_speaker_ids.pop(0)
                                    
                                    unique_recent_speakers = list(set(self.recent_speaker_ids[-10:]))
                                    if len(unique_recent_speakers) > 1:
                                        speaker_counts = {}
                                        for s in self.recent_speaker_ids[-10:]:
                                            speaker_counts[s] = speaker_counts.get(s, 0) + 1
                                        
                                        if self.last_speaker_id and spk == self.last_speaker_id:
                                            for recent_spk, count in speaker_counts.items():
                                                if recent_spk != self.last_speaker_id and count >= 2:
                                                    spk = recent_spk
                                                    break
                                    
                                    self.last_speaker_id = spk
                                
                                label = label_for_speaker_id(spk)
                                ev_type = getattr(ev, "type", None)
                                ev_type_name = getattr(ev_type, "name", str(ev_type)) if ev_type else None
                                is_final = ev_type_name and "FINAL" in ev_type_name.upper()
                                
                                text_stripped = text.strip()
                                if text_stripped and is_final:
                                    timestamp = datetime.now().isoformat()
                                    self._append_to_json(label, text_stripped, timestamp)
                        except Exception as e:
                            # Log error but continue processing
                            logger.error(f"Error processing speech event: {e}")
                            continue
                    
                    yield ev
                
                # Flush buffer on exit
                self._flush_transcript_buffer()
                
                if speech_event_count == 0:
                    logger.warning("No speech events received - RTMP stream may not be connected or no audio in stream")
                    
            except Exception as e:
                # Flush buffer on error
                self._flush_transcript_buffer()
                # Handle channel closed errors gracefully
                if "ChanClosed" in str(type(e).__name__) or "channel" in str(e).lower():
                    pass  # Expected during cleanup
                else:
                    logger.error(f"Error in transcription: {e}", exc_info=True)
                    # Don't raise - allow graceful continuation if possible

        return _transcribe()

    def start_recording(self):
        """Start recording - set state to recording"""
        if self.recording_state == "idle" or self.recording_state == "stopped":
            self.recording_state = "recording"
            if self.recording_state_service and self.remote_session_id:
                self.recording_state_service.update_agent_state(
                    self.remote_session_id,
                    "recording"
                )
    
    def stop_recording(self):
        """Stop recording - set state to stopped and disconnect from room"""
        if self.recording_state in ["recording", "paused"]:
            self.recording_state = "stopped"
            self._should_disconnect = True
            # Flush buffer before stopping
            self._flush_transcript_buffer()
            if self.recording_state_service and self.remote_session_id:
                self.recording_state_service.update_agent_state(
                    self.remote_session_id,
                    "stopped"
                )
            if self.ctx.room:
                try:
                    pass  # Disconnect handled in stt_node
                except Exception as e:
                    logger.error(f"Error disconnecting from room: {e}")
    
    def pause_recording(self):
        """Pause recording - set state to paused"""
        if self.recording_state == "recording":
            self.recording_state = "paused"
            if self.recording_state_service and self.remote_session_id:
                self.recording_state_service.update_agent_state(
                    self.remote_session_id,
                    "paused"
                )
    
    def resume_recording(self):
        """Resume recording - set state to recording"""
        if self.recording_state == "paused":
            self.recording_state = "recording"
            if self.recording_state_service and self.remote_session_id:
                self.recording_state_service.update_agent_state(
                    self.remote_session_id,
                    "recording"
                )

    def llm_node(self, chat_ctx, tools, model_settings):
        async def _silent():
            if False: yield ""
        return _silent()

    def tts_node(self, text, model_settings):
        async def _silent():
            async for _ in text: pass
            if False: yield rtc.AudioFrame()
        return _silent()


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the transcription agent"""
    global speaker_label_map, next_speaker_num
    
    # Reset for new session
    speaker_label_map = {}
    next_speaker_num = 1
    
    room_name = ctx.room.name if ctx.room else "Meeting"
    
    if not ctx.room:
        logger.warning("No room context available")
        return
    
    # Get STT model from environment (defaults to Speechmatics)
    stt_model = os.environ.get("STT_MODEL", "speechmatics").lower()
    
    # Verify Speechmatics API key is set
    if stt_model == "speechmatics":
        speechmatics_key = os.environ.get("SPEECHMATICS_API_KEY", "")
        if not speechmatics_key or speechmatics_key.strip() == "":
            logger.error("SPEECHMATICS_API_KEY is not set in environment!")
            raise RuntimeError(
                "SPEECHMATICS_API_KEY environment variable is required. "
                "Please set it in your .env.local file."
            )
    
    # Initialize STT using unified service
    # The service will automatically handle provider selection and API key retrieval
    from infrastructure.services.unified_stt_service import UnifiedSTTService
    stt_service = UnifiedSTTService()
    
    # Get diarization configuration based on STT model
    from application.services.speaker_diarization_service import SpeakerDiarizationService
    diarization_service = SpeakerDiarizationService()
    
    # Determine if manual diarization is needed
    needs_manual_diarization = stt_model in ["deepgram", "assemblyai"]
    
    stt_kwargs = {
        "language": "en",
        "enable_diarization": True,  # Enable native diarization for Speechmatics
    }
    
    # Add model-specific diarization configuration
    diarization_config = diarization_service.get_stt_diarization_config()
    stt_kwargs.update(diarization_config)
    
    stt_engine = stt_service.create_stt_engine(**stt_kwargs)
    
    # Try to initialize turn detector, but make it optional if PyTorch is not available
    turn_detection = None
    enable_turn_detector = os.environ.get("ENABLE_TURN_DETECTOR", "false").lower() == "true"
    
    if enable_turn_detector and TURN_DETECTOR_AVAILABLE and MultilingualModel:
        try:
            turn_detection = MultilingualModel()
        except Exception as e:
            logger.warning(f"Failed to initialize turn detector: {e}. Continuing without it.")
            turn_detection = None
    
    # Initialize VAD (Voice Activity Detection)
    try:
        vad = silero.VAD.load()
    except Exception as e:
        logger.warning(f"Failed to load VAD: {e}. Continuing without it.")
        vad = None
    
    # Create agent session with optional turn detection
    # If turn_detection is None, the session will work without it
    session = AgentSession(
        llm="google/gemini-2.5-flash",
        stt=stt_engine,
        vad=vad,
        turn_detection=turn_detection,  # Can be None - agent will work without it
    )
    
    # Create agent instance
    agent = DiarizationAgent(ctx)
    
    # Store turn detector reference in agent for manual diarization
    if needs_manual_diarization and turn_detection:
        agent._turn_detector = turn_detection
    
    # Register agent in global registry for remote control access
    _active_agents[room_name] = agent
    
    # Add event handlers for participant and track events
    def on_participant_connected(participant: rtc.RemoteParticipant):
        """Handle participant connected event"""
        pass
    
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        """Handle track published event"""
        pass
    
    if ctx.room:
        ctx.room.on("participant_connected", on_participant_connected)
        ctx.room.on("track_published", on_track_published)
    
    try:
        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
        )
    except Exception as e:
        error_str = str(e).lower()
        
        # Handle expected errors gracefully
        if PortAudioError and isinstance(e, PortAudioError) or "portaudio" in error_str or "sounddevice" in error_str:
            pass  # Ignore local microphone errors
        elif "chanclosed" in error_str or "channel" in error_str or "channel closed" in error_str:
            pass  # Expected during cleanup
        elif "roomclosed" in error_str or "room closed" in error_str or "disconnected" in error_str:
            pass  # Expected
        else:
            logger.error(f"Unexpected error in agent session for {room_name}: {e}", exc_info=True)
            raise
    finally:
        # Flush buffer and unregister agent when session ends
        agent._flush_transcript_buffer()
        if room_name in _active_agents:
            del _active_agents[room_name]


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))