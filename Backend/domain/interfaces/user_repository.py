"""
User Repository Interface

Defines the contract for user data persistence.
Following Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..entities.user import User


class IUserRepository(ABC):
    """Interface for user repository operations"""
    
    @abstractmethod
    def create(self, user: User) -> User:
        """
        Create a new user.
        
        Args:
            user: The user entity to create
            
        Returns:
            Created User entity
            
        Raises:
            ValueError: If user with email or username already exists
        """
        pass
    
    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find a user by ID.
        
        Args:
            user_id: The user ID to find
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by email.
        
        Args:
            email: The email to search for
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """
        Find a user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update(self, user: User) -> User:
        """
        Update an existing user.
        
        Args:
            user: The user entity with updated fields
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If email or username is already taken by another user
        """
        pass

