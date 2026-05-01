"""
Update User Username Use Case

Use case for updating user username.
"""
from typing import Dict
from application.services.auth_service import AuthService


class UpdateUserUsernameUseCase:
    """Use case for updating user username"""
    
    def __init__(self, auth_service: AuthService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service
    
    def execute(self, user_id: str, new_username: str) -> Dict:
        """
        Execute username update.
        
        Args:
            user_id: The user ID
            new_username: New username
            
        Returns:
            Dictionary with updated user information
            
        Raises:
            ValueError: If update fails (username already taken, validation error)
        """
        user = self.auth_service.update_username(user_id, new_username)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }

