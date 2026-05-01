"""
Transcript WebSocket Handler

Handles WebSocket connections for real-time transcript updates.
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from domain.interfaces.file_storage import IFileStorage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for transcript updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.last_entry_counts: Dict[str, int] = {}
    
    async def connect(self, websocket: WebSocket, room_name: str):
        """Connect a WebSocket for a room"""
        try:
            await websocket.accept()
            if room_name not in self.active_connections:
                self.active_connections[room_name] = set()
                self.last_entry_counts[room_name] = 0
            self.active_connections[room_name].add(websocket)
            logger.info(f"WebSocket connected for room: {room_name}")
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket, room_name: str):
        """Disconnect a WebSocket"""
        if room_name in self.active_connections:
            self.active_connections[room_name].discard(websocket)
            if not self.active_connections[room_name]:
                del self.active_connections[room_name]
                if room_name in self.last_entry_counts:
                    del self.last_entry_counts[room_name]
    
    async def send_transcript_update(self, room_name: str, transcript_entry: dict):
        """Send transcript update to all connected clients for a room"""
        if room_name in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[room_name]:
                try:
                    await connection.send_json({
                        "type": "transcript_update",
                        "data": transcript_entry
                    })
                except Exception:
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[room_name].discard(conn)
    
    async def send_agent_status(self, room_name: str, status: str, timestamp: str):
        """Send agent status update to all connected clients for a room"""
        if room_name in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[room_name]:
                try:
                    await connection.send_json({
                        "type": "agent_status",
                        "data": {
                            "status": status,
                            "room_name": room_name,
                            "timestamp": timestamp
                        }
                    })
                except Exception:
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[room_name].discard(conn)


class TranscriptFileHandler(FileSystemEventHandler):
    """File system event handler for transcript file updates"""
    
    def __init__(self, manager: ConnectionManager, file_storage: IFileStorage, loop, transcripts_dir: Path):
        self.manager = manager
        self.file_storage = file_storage
        self.processing_files: Set[str] = set()
        self.loop = loop
        self.transcripts_dir = transcripts_dir
        self.processed_status_files: Set[str] = set()
    
    def on_created(self, event):
        """Handle file creation events (for agent status files)"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('_agent_status.json'):
            if event.src_path in self.processing_files:
                return
            
            self.processing_files.add(event.src_path)
            asyncio.run_coroutine_threadsafe(
                self.process_status_file(event.src_path),
                self.loop
            )
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.json') and not event.src_path.endswith('_agent_status.json'):
            # Avoid processing the same file multiple times rapidly
            if event.src_path in self.processing_files:
                return
            
            self.processing_files.add(event.src_path)
            # Schedule async task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_file_update(event.src_path),
                self.loop
            )
    
    async def process_status_file(self, file_path: str):
        """Process agent status file to notify frontend"""
        try:
            # Only process each status file once
            if file_path in self.processed_status_files:
                return
            
            data = self.file_storage.read_file(Path(file_path))
            if not data:
                return
            
            room_name = data.get("room_name")
            status = data.get("status")
            timestamp = data.get("timestamp")
            
            if room_name and status == "started":
                await self.manager.send_agent_status(room_name, status, timestamp)
                self.processed_status_files.add(file_path)
        except Exception as e:
            logger.error(f"Error processing status file: {e}")
        finally:
            self.processing_files.discard(file_path)
    
    async def process_file_update(self, file_path: str):
        """Process transcript file update"""
        try:
            # Extract room name from filename
            filename = Path(file_path).stem
            parts = filename.rsplit('_', 2)
            if len(parts) >= 3:
                room_name = parts[0]
            elif len(parts) == 2:
                room_name = parts[0]
            else:
                room_name = filename
            
            # Read the file
            data = self.file_storage.read_file(Path(file_path))
            if not data:
                return
            
            current_count = len(data.get('transcripts', []))
            last_count = self.manager.last_entry_counts.get(room_name, 0)
            
            if current_count > last_count:
                # Get new entries
                new_entries = data['transcripts'][last_count:]
                self.manager.last_entry_counts[room_name] = current_count
                
                # Send each new entry to connected clients
                for entry in new_entries:
                    await self.manager.send_transcript_update(room_name, entry)
        except Exception as e:
            logger.error(f"Error processing file update: {e}")
        finally:
            self.processing_files.discard(file_path)


class TranscriptWebSocketManager:
    """Manages WebSocket connections and file watching for transcripts"""
    
    def __init__(self, file_storage: IFileStorage, transcripts_dir: Path):
        self.connection_manager = ConnectionManager()
        self.file_storage = file_storage
        self.transcripts_dir = transcripts_dir
        self.event_handler = None
        self.observer = None
    
    async def handle_websocket(self, websocket: WebSocket, room_name: str):
        """Handle WebSocket connection for transcript updates"""
        logger.info(f"WebSocket connection attempt for room: {room_name}")
        try:
            await self.connection_manager.connect(websocket, room_name)
            logger.info(f"WebSocket connected successfully for room: {room_name}")
            # Send initial transcript data if file exists
            transcript_file = None
            for file in self.transcripts_dir.glob(f"{room_name}_*.json"):
                transcript_file = file
                break
            
            if transcript_file and transcript_file.exists():
                data = self.file_storage.read_file(transcript_file)
                if data:
                    await websocket.send_json({
                        "type": "initial_data",
                        "data": {
                            "meeting_name": data.get("meeting_name", room_name),
                            "transcripts": data.get("transcripts", []),
                            "start_time": data.get("start_time"),
                            "total_entries": data.get("total_entries", 0)
                        }
                    })
                    self.connection_manager.last_entry_counts[room_name] = len(
                        data.get('transcripts', [])
                    )
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    data = await websocket.receive_text()
                    # Echo back or handle ping
                    if data == "ping":
                        await websocket.send_text("pong")
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for room: {room_name}")
                    break
        except Exception as e:
            logger.error(f"WebSocket error in handler: {e}", exc_info=True)
        finally:
            self.connection_manager.disconnect(websocket, room_name)
    
    def start_file_watcher(self, loop):
        """Start file watcher for transcript updates"""
        self.event_handler = TranscriptFileHandler(
            self.connection_manager,
            self.file_storage,
            loop,
            self.transcripts_dir
        )
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.transcripts_dir),
            recursive=False
        )
        self.observer.start()
    
    def stop_file_watcher(self):
        """Stop file watcher"""
        if self.observer:
            self.observer.stop()
            self.observer.join()

