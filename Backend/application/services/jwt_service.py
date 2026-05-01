"""
JWT Service

Handles JWT token generation and validation.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv(".env.local")

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default


class JWTService:
    """Service for JWT token operations"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Dictionary containing claims (e.g., {"sub": user_id})
            expires_delta: Optional expiration time delta
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """
        Extract user ID from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID if token is valid, None otherwise
        """
        payload = JWTService.verify_token(token)
        if payload is None:
            return None
        return payload.get("sub")  # Standard JWT claim for subject (user ID)

