"""
Authentication Middleware

JWT authentication middleware for protecting routes.
"""
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from application.services.jwt_service import JWTService

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and validate user ID from JWT token.
    Used as a FastAPI dependency.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials
    user_id = JWTService.get_user_id_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id

