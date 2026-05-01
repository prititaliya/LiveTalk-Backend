"""
Update User Email Use Case

Use case for updating user email.
"""
from typing import Dict
from application.services.auth_service import AuthService


class UpdateUserEmailUseCase:
    """Use case for updating user email"""
    
    def __init__(self, auth_service: AuthService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service
    
    def execute(self, user_id: str, new_email: str) -> Dict:
        """
        Execute email update.
        
        Args:
            user_id: The user ID
            new_email: New email address
            
        Returns:
            Dictionary with updated user information
            
        Raises:
            ValueError: If update fails (email already taken, validation error)
        """
        user = self.auth_service.update_email(user_id, new_email)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }

