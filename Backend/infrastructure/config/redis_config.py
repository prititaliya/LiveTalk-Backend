"""
Redis Configuration

Manages Redis connection configuration and client creation.
"""
import os
import logging
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv(".env.local")

logger = logging.getLogger(__name__)

# Redis configuration from environment variables
REDIS_URL = os.environ.get("REDIS_URL")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create a Redis client instance.
    Uses connection pooling for efficient connection management.
    
    Returns:
        Redis client instance
        
    Raises:
        redis.ConnectionError: If connection fails
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            if REDIS_URL:
                # Use Redis URL (for Redis Cloud or custom configurations)
                _redis_client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
            else:
                # Use individual connection parameters
                _redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    password=REDIS_PASSWORD,
                    db=REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
            
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")
            raise
    
    return _redis_client


def close_redis_client():
    """Close the Redis client connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def test_redis_connection() -> bool:
    """Test if Redis connection is working"""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

