"""
User Entity

Domain entity representing a user.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """A user entity"""
    id: str
    email: str
    username: str
    password_hash: str
    created_at: datetime
    email_verified: bool = False
    
    def __post_init__(self):
        """Validate user data"""
        if not self.id:
            raise ValueError("User ID cannot be empty")
        if not self.email:
            raise ValueError("Email cannot be empty")
        if not self.username:
            raise ValueError("Username cannot be empty")
        if not self.password_hash:
            raise ValueError("Password hash cannot be empty")
        if not isinstance(self.created_at, datetime):
            raise ValueError("Created at must be a datetime object")
    
    def __eq__(self, other):
        """Check equality based on ID"""
        if not isinstance(other, User):
            return False
        return self.id == other.id
    
    def __hash__(self):
        """Make User hashable"""
        return hash(self.id)

