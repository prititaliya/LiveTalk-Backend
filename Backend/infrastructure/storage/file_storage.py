"""
File Storage Implementation

Implements IFileStorage interface for file system operations.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from domain.interfaces.file_storage import IFileStorage


class FileStorage(IFileStorage):
    """File system storage implementation"""
    
    def __init__(self, base_directory: Path):
        """
        Initialize file storage with base directory.
        
        Args:
            base_directory: Base directory for file operations
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def create_file(self, file_path: Path, initial_data: Dict) -> None:
        """Create a new file with initial data"""
        full_path = self._resolve_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    def read_file(self, file_path: Path) -> Optional[Dict]:
        """Read data from a file"""
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to read file {file_path}: {e}")
    
    def append_to_file(self, file_path: Path, data: Dict) -> None:
        """Append data to an existing file"""
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read existing data
        existing_data = self.read_file(file_path)
        if existing_data is None:
            raise ValueError(f"Could not read existing file: {file_path}")
        
        # Append new data (assuming it's a transcript entry)
        if "transcripts" in existing_data and isinstance(existing_data["transcripts"], list):
            if "transcripts" in data:
                existing_data["transcripts"].extend(data["transcripts"])
            else:
                existing_data["transcripts"].append(data)
            
            # Update metadata
            existing_data["total_entries"] = len(existing_data["transcripts"])
            from datetime import datetime
            existing_data["last_updated"] = datetime.now().isoformat()
        
        # Write back
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if a file exists"""
        full_path = self._resolve_path(file_path)
        return full_path.exists()
    
    def find_files_by_pattern(self, pattern: str) -> List[Path]:
        """Find files matching a pattern"""
        return list(self.base_directory.glob(pattern))
    
    def _resolve_path(self, file_path: Path) -> Path:
        """Resolve file path relative to base directory"""
        if file_path.is_absolute():
            return file_path
        return self.base_directory / file_path

