"""
OTP Service

Service for generating, storing, and verifying OTP (One-Time Password) codes.
"""
import random
import logging
from typing import Optional
from infrastructure.config.redis_config import get_redis_client

logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP generation and verification"""
    
    def __init__(self, redis_client=None):
        """
        Initialize OTP service.
        
        Args:
            redis_client: Optional Redis client (uses get_redis_client() if not provided)
        """
        self.redis_client = redis_client or get_redis_client()
    
    def generate_otp(self, length: int = 6) -> str:
        """
        Generate a random numeric OTP code.
        
        Args:
            length: Length of OTP code (default: 6)
            
        Returns:
            OTP code as string (e.g., "123456")
        """
        return "".join([str(random.randint(0, 9)) for _ in range(length)])
    
    def store_otp(self, identifier: str, otp: str, expiry_seconds: int = 600) -> None:
        """
        Store OTP in Redis with expiration.
        
        Args:
            identifier: Unique identifier (e.g., email address or user_id)
            otp: OTP code to store
            expiry_seconds: Expiration time in seconds (default: 600 = 10 minutes)
        """
        try:
            redis_key = f"otp:email:{identifier}"
            self.redis_client.setex(redis_key, expiry_seconds, otp)
            logger.info(f"OTP stored for identifier: {identifier}")
        except Exception as e:
            logger.error(f"Error storing OTP for {identifier}: {str(e)}", exc_info=True)
            raise
    
    def verify_otp(self, identifier: str, otp: str) -> bool:
        """
        Verify OTP code and delete it from Redis if valid.
        
        Args:
            identifier: Unique identifier (e.g., email address or user_id)
            otp: OTP code to verify
            
        Returns:
            True if OTP is valid, False otherwise
        """
        try:
            redis_key = f"otp:email:{identifier}"
            stored_otp = self.redis_client.get(redis_key)
            
            if stored_otp is None:
                logger.warning(f"OTP not found or expired for identifier: {identifier}")
                return False
            
            # Compare OTP codes (case-insensitive, strip whitespace)
            if stored_otp.strip() == otp.strip():
                # Delete OTP after successful verification (one-time use)
                self.redis_client.delete(redis_key)
                logger.info(f"OTP verified successfully for identifier: {identifier}")
                return True
            else:
                logger.warning(f"Invalid OTP provided for identifier: {identifier}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying OTP for {identifier}: {str(e)}", exc_info=True)
            return False
    
    def delete_otp(self, identifier: str) -> None:
        """
        Delete OTP from Redis (cleanup).
        
        Args:
            identifier: Unique identifier (e.g., email address or user_id)
        """
        try:
            redis_key = f"otp:email:{identifier}"
            self.redis_client.delete(redis_key)
            logger.info(f"OTP deleted for identifier: {identifier}")
        except Exception as e:
            logger.error(f"Error deleting OTP for {identifier}: {str(e)}", exc_info=True)
    
    def get_otp(self, identifier: str) -> Optional[str]:
        """
        Get stored OTP without deleting it (for testing/debugging).
        
        Args:
            identifier: Unique identifier (e.g., email address or user_id)
            
        Returns:
            OTP code if found, None otherwise
        """
        try:
            redis_key = f"otp:email:{identifier}"
            return self.redis_client.get(redis_key)
        except Exception as e:
            logger.error(f"Error getting OTP for {identifier}: {str(e)}", exc_info=True)
            return None

