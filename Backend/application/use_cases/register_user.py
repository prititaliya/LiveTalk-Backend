"""
Register User Use Case

Use case for user registration.
"""
from typing import Dict
from application.services.auth_service import AuthService


class RegisterUserUseCase:
    """Use case for registering a new user"""
    
    def __init__(self, auth_service: AuthService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service
    
    def execute(self, email: str, username: str, password: str) -> Dict:
        """
        Execute user registration.
        
        Args:
            email: User email
            username: User username
            password: Plain text password
            
        Returns:
            Dictionary with user information
            
        Raises:
            ValueError: If registration fails (duplicate email/username, validation error)
        """
        user = self.auth_service.register_user(email, username, password)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat()
        }

