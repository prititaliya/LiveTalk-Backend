"""
User Repository Implementation

Implements IUserRepository interface using PostgreSQL.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from domain.interfaces.user_repository import IUserRepository
from domain.entities.user import User
from infrastructure.database.models import UserModel
from data_access.mappers.user_mapper import to_domain, to_model


class UserRepository(IUserRepository):
    """PostgreSQL implementation of user repository"""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, user: User) -> User:
        """Create a new user in the database"""
        try:
            user_model = to_model(user)
            self.db.add(user_model)
            self.db.commit()
            self.db.refresh(user_model)
            return to_domain(user_model)
        except IntegrityError as e:
            self.db.rollback()
            # Get detailed error information
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
            
            # Check constraint name in error message
            constraint_name = None
            if hasattr(e, 'orig') and hasattr(e.orig, 'diag'):
                constraint_name = getattr(e.orig.diag, 'constraint_name', None)
            
            # Check for email constraint violation
            if (constraint_name and ('email' in constraint_name.lower() or 'users_email_key' in constraint_name)) or \
               ('email' in error_msg.lower() and 'unique' in error_msg.lower()) or \
               ('users_email_key' in error_msg):
                # Double-check by querying
                existing = self.find_by_email(user.email)
                if existing:
                    raise ValueError(f"User with email '{user.email}' already exists")
                else:
                    raise ValueError(f"Email '{user.email}' is already taken")
            
            # Check for username constraint violation
            elif (constraint_name and ('username' in constraint_name.lower() or 'users_username_key' in constraint_name)) or \
                 ('username' in error_msg.lower() and 'unique' in error_msg.lower()) or \
                 ('users_username_key' in error_msg):
                # Double-check by querying
                existing = self.find_by_username(user.username)
                if existing:
                    raise ValueError(f"User with username '{user.username}' already exists")
                else:
                    raise ValueError(f"Username '{user.username}' is already taken")
            
            # Generic error with more details for debugging
            raise ValueError(f"User with this email or username already exists. Constraint: {constraint_name}, Error: {error_msg[:200]}")
    
    def find_by_id(self, user_id: str) -> Optional[User]:
        """Find a user by ID"""
        user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user_model is None:
            return None
        return to_domain(user_model)
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by email"""
        user_model = self.db.query(UserModel).filter(UserModel.email == email).first()
        if user_model is None:
            return None
        return to_domain(user_model)
    
    def find_by_username(self, username: str) -> Optional[User]:
        """Find a user by username"""
        user_model = self.db.query(UserModel).filter(UserModel.username == username).first()
        if user_model is None:
            return None
        return to_domain(user_model)
    
    def update(self, user: User) -> User:
        """Update an existing user in the database"""
        try:
            # Find existing user
            user_model = self.db.query(UserModel).filter(UserModel.id == user.id).first()
            if user_model is None:
                raise ValueError(f"User with id '{user.id}' not found")
            
            # Check if email is already taken by another user
            existing_by_email = self.find_by_email(user.email)
            if existing_by_email and existing_by_email.id != user.id:
                raise ValueError(f"User with email '{user.email}' already exists")
            
            # Check if username is already taken by another user
            existing_by_username = self.find_by_username(user.username)
            if existing_by_username and existing_by_username.id != user.id:
                raise ValueError(f"User with username '{user.username}' already exists")
            
            # Update fields
            user_model.email = user.email
            user_model.username = user.username
            user_model.password_hash = user.password_hash
            user_model.email_verified = user.email_verified
            # Note: created_at should not be updated
            
            self.db.commit()
            self.db.refresh(user_model)
            return to_domain(user_model)
        except IntegrityError as e:
            self.db.rollback()
            # Get detailed error information
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            constraint_name = None
            if hasattr(e, 'orig') and hasattr(e.orig, 'diag'):
                constraint_name = getattr(e.orig.diag, 'constraint_name', None)
            
            # Check for email constraint violation
            if (constraint_name and ('email' in constraint_name.lower() or 'users_email_key' in constraint_name)) or \
               ('email' in error_msg.lower() and 'unique' in error_msg.lower()) or \
               ('users_email_key' in error_msg):
                existing = self.find_by_email(user.email)
                if existing and existing.id != user.id:
                    raise ValueError(f"Email '{user.email}' is already taken")
            
            # Check for username constraint violation
            elif (constraint_name and ('username' in constraint_name.lower() or 'users_username_key' in constraint_name)) or \
                 ('username' in error_msg.lower() and 'unique' in error_msg.lower()) or \
                 ('users_username_key' in error_msg):
                existing = self.find_by_username(user.username)
                if existing and existing.id != user.id:
                    raise ValueError(f"Username '{user.username}' is already taken")
            
            # Generic error
            raise ValueError(f"Failed to update user: {error_msg[:200]}")
        except ValueError:
            # Re-raise ValueError (already formatted)
            raise
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update user: {str(e)}")

