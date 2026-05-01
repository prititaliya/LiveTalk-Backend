"""
SQLAlchemy Database Models

Database models for SQLAlchemy ORM.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class UserModel(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email}, username={self.username})>"

