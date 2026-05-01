"""
Login User Use Case

Use case for user authentication/login.
"""
from typing import Dict, Optional
from application.services.auth_service import AuthService
from application.services.jwt_service import JWTService


class LoginUserUseCase:
    """Use case for user login"""
    
    def __init__(self, auth_service: AuthService, jwt_service: JWTService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
            jwt_service: JWT service for token generation
        """
        self.auth_service = auth_service
        self.jwt_service = jwt_service
    
    def execute(self, email_or_username: str, password: str) -> Optional[Dict]:
        """
        Execute user login.
        
        Args:
            email_or_username: User email or username
            password: Plain text password
            
        Returns:
            Dictionary with access token and user info if successful, None otherwise
        """
        # Authenticate user
        user = self.auth_service.authenticate_user(email_or_username, password)
        
        if user is None:
            return None
        
        # Generate access token
        access_token = self.jwt_service.create_access_token(
            data={"sub": user.id}  # "sub" is standard JWT claim for subject
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified
        }

