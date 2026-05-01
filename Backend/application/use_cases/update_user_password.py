"""
Update User Password Use Case

Use case for updating user password.
"""
from typing import Dict
from application.services.auth_service import AuthService


class UpdateUserPasswordUseCase:
    """Use case for updating user password"""
    
    def __init__(self, auth_service: AuthService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service
    
    def execute(self, user_id: str, current_password: str, new_password: str) -> Dict:
        """
        Execute password update.
        
        Args:
            user_id: The user ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Dictionary with updated user information (password hash not included)
            
        Raises:
            ValueError: If update fails (current password incorrect, validation error)
        """
        user = self.auth_service.update_password(user_id, current_password, new_password)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }

