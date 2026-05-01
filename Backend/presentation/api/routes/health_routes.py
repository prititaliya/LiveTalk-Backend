"""
Health Check Routes

Health check endpoint for monitoring.
"""
from fastapi import APIRouter
from presentation.dto.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

