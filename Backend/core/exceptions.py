"""
Custom Exceptions

Domain-specific exceptions for the application.
"""


class TranscriptNotFoundError(Exception):
    """Raised when a transcript is not found"""
    pass


class InvalidTranscriptError(Exception):
    """Raised when transcript data is invalid"""
    pass


class StorageError(Exception):
    """Raised when storage operations fail"""
    pass

