"""
Get Current User Use Case

Use case for getting current authenticated user information.
"""
from typing import Dict, Optional
from domain.interfaces.user_repository import IUserRepository


class GetCurrentUserUseCase:
    """Use case for getting current user information"""
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize use case.
        
        Args:
            user_repository: User repository
        """
        self.user_repository = user_repository
    
    def execute(self, user_id: str) -> Optional[Dict]:
        """
        Execute getting current user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with user information, or None if user not found
        """
        user = self.user_repository.find_by_id(user_id)
        
        if not user:
            return None
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }

