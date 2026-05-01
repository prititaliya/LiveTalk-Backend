"""
File Storage Interface

Defines the contract for file system operations.
Following Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class IFileStorage(ABC):
    """Interface for file storage operations"""
    
    @abstractmethod
    def create_file(self, file_path: Path, initial_data: Dict) -> None:
        """
        Create a new file with initial data.
        
        Args:
            file_path: Path where file should be created
            initial_data: Initial data to write to file
        """
        pass
    
    @abstractmethod
    def read_file(self, file_path: Path) -> Optional[Dict]:
        """
        Read data from a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Dictionary with file data, or None if file doesn't exist
        """
        pass
    
    @abstractmethod
    def append_to_file(self, file_path: Path, data: Dict) -> None:
        """
        Append data to an existing file.
        
        Args:
            file_path: Path to the file
            data: Data to append
        """
        pass
    
    @abstractmethod
    def file_exists(self, file_path: Path) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def find_files_by_pattern(self, pattern: str) -> List[Path]:
        """
        Find files matching a pattern.
        
        Args:
            pattern: File pattern to match (e.g., "room_*.json")
            
        Returns:
            List of matching file paths
        """
        pass

