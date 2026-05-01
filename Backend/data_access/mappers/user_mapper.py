"""
User Mapper

Maps between SQLAlchemy UserModel and User domain entity.
"""
from datetime import datetime
from typing import Optional

from domain.entities.user import User
from infrastructure.database.models import UserModel


def to_domain(user_model: UserModel) -> User:
    """
    Convert SQLAlchemy UserModel to User domain entity.
    
    Args:
        user_model: SQLAlchemy model instance
        
    Returns:
        User domain entity
    """
    return User(
        id=str(user_model.id),
        email=user_model.email,
        username=user_model.username,
        password_hash=user_model.password_hash,
        created_at=user_model.created_at,
        email_verified=getattr(user_model, 'email_verified', False)
    )


def to_model(user: User) -> UserModel:
    """
    Convert User domain entity to SQLAlchemy UserModel.
    
    Args:
        user: User domain entity
        
    Returns:
        SQLAlchemy UserModel instance
    """
    import uuid
    return UserModel(
        id=uuid.UUID(user.id) if isinstance(user.id, str) else user.id,
        email=user.email,
        username=user.username,
        password_hash=user.password_hash,
        created_at=user.created_at,
        email_verified=user.email_verified
    )

