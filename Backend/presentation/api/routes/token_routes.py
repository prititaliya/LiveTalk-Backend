"""
Token Routes

Routes for LiveKit token generation.
"""
from fastapi import APIRouter, HTTPException
from presentation.dto.requests import TokenRequest
from presentation.dto.responses import TokenResponse
from application.use_cases.generate_token import GenerateTokenUseCase

router = APIRouter()


def create_token_router(generate_token_use_case: GenerateTokenUseCase) -> APIRouter:
    """
    Create token router with dependencies.
    
    Args:
        generate_token_use_case: Use case for token generation
        
    Returns:
        Configured APIRouter
    """
    @router.post("/api/token", response_model=TokenResponse)
    async def get_token(request: TokenRequest):
        """Generate a LiveKit access token for joining a room"""
        try:
            result = generate_token_use_case.execute(
                participant_name=request.participant_name,
                room_name=request.room_name,
                can_publish=True,
                can_subscribe=True
            )
            return TokenResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"LiveKit configuration error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate token: {str(e)}"
            )
    
    return router

