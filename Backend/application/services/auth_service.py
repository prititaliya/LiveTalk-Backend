"""
Authentication Service

Handles user authentication operations (password hashing, verification).
"""
import uuid
from datetime import datetime
from typing import Optional
from passlib.context import CryptContext

from domain.entities.user import User
from domain.interfaces.user_repository import IUserRepository

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize auth service.
        
        Args:
            user_repository: Repository for user operations
        """
        self.user_repository = user_repository
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def register_user(self, email: str, username: str, password: str) -> User:
        """
        Register a new user.
        
        Args:
            email: User email
            username: User username
            password: Plain text password
            
        Returns:
            Created User entity
            
        Raises:
            ValueError: If email or username already exists, or validation fails
        """
        # Validate input
        if not email or not email.strip():
            raise ValueError("Email is required")
        if not username or not username.strip():
            raise ValueError("Username is required")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        
        # Check if user already exists (case-insensitive for email, case-sensitive for username)
        email_lower = email.strip().lower()
        username_trimmed = username.strip()
        
        existing_by_email = self.user_repository.find_by_email(email_lower)
        if existing_by_email:
            raise ValueError(f"User with email '{email}' already exists")
        
        existing_by_username = self.user_repository.find_by_username(username_trimmed)
        if existing_by_username:
            raise ValueError(f"User with username '{username}' already exists")
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Create user entity (email already lowercased, username trimmed)
        # New users start with email_verified=False
        user = User(
            id=str(uuid.uuid4()),
            email=email_lower,
            username=username_trimmed,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
            email_verified=False
        )
        
        # Save user
        return self.user_repository.create(user)
    
    def authenticate_user(self, email_or_username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email/username and password.
        
        Args:
            email_or_username: User email or username
            password: Plain text password
            
        Returns:
            User entity if authentication succeeds, None otherwise
        """
        # Find user by email or username
        user = self.user_repository.find_by_email(email_or_username)
        if user is None:
            user = self.user_repository.find_by_username(email_or_username)
        
        if user is None:
            return None
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            return None
        
        return user
    
    def update_email(self, user_id: str, new_email: str) -> User:
        """
        Update user email.
        
        Args:
            user_id: User ID
            new_email: New email address
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If email is invalid or already taken
        """
        # Validate input
        if not new_email or not new_email.strip():
            raise ValueError("Email is required")
        
        # Basic email validation (simple regex check)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, new_email.strip()):
            raise ValueError("Invalid email format")
        
        # Get existing user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Normalize email (lowercase)
        email_lower = new_email.strip().lower()
        
        # Check if email is already taken by another user
        existing_by_email = self.user_repository.find_by_email(email_lower)
        if existing_by_email and existing_by_email.id != user_id:
            raise ValueError(f"User with email '{new_email}' already exists")
        
        # If email is the same, no update needed
        if user.email == email_lower:
            return user
        
        # Update email and mark as unverified (requires re-verification)
        updated_user = User(
            id=user.id,
            email=email_lower,
            username=user.username,
            password_hash=user.password_hash,
            created_at=user.created_at,
            email_verified=False  # Require re-verification when email changes
        )
        
        return self.user_repository.update(updated_user)
    
    def update_username(self, user_id: str, new_username: str) -> User:
        """
        Update user username.
        
        Args:
            user_id: User ID
            new_username: New username
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If username is invalid or already taken
        """
        # Validate input
        if not new_username or not new_username.strip():
            raise ValueError("Username is required")
        
        username_trimmed = new_username.strip()
        
        # Username validation
        if len(username_trimmed) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        # Get existing user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Check if username is already taken by another user
        existing_by_username = self.user_repository.find_by_username(username_trimmed)
        if existing_by_username and existing_by_username.id != user_id:
            raise ValueError(f"User with username '{new_username}' already exists")
        
        # If username is the same, no update needed
        if user.username == username_trimmed:
            return user
        
        # Update username (preserve email_verified status)
        updated_user = User(
            id=user.id,
            email=user.email,
            username=username_trimmed,
            password_hash=user.password_hash,
            created_at=user.created_at,
            email_verified=user.email_verified
        )
        
        return self.user_repository.update(updated_user)
    
    def update_password(self, user_id: str, current_password: str, new_password: str) -> User:
        """
        Update user password.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If password is invalid or current password is incorrect
        """
        # Validate input
        if not current_password:
            raise ValueError("Current password is required")
        if not new_password:
            raise ValueError("New password is required")
        if len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(new_password) > 72:
            raise ValueError("Password must be at most 72 characters")
        
        # Get existing user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify current password
        if not self.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Hash new password
        new_password_hash = self.hash_password(new_password)
        
        # Update password (preserve email_verified status)
        updated_user = User(
            id=user.id,
            email=user.email,
            username=user.username,
            password_hash=new_password_hash,
            created_at=user.created_at,
            email_verified=user.email_verified
        )
        
        return self.user_repository.update(updated_user)
    
    def verify_email(self, user_id: str, otp: str, otp_service, email: str) -> User:
        """
        Verify user email with OTP code.
        
        Args:
            user_id: User ID
            otp: OTP code to verify
            otp_service: OTPService instance for verification
            email: Email address associated with the OTP
            
        Returns:
            Updated User entity with email_verified=True
            
        Raises:
            ValueError: If OTP is invalid or expired
        """
        # Get existing user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify OTP
        if not otp_service.verify_otp(email, otp):
            raise ValueError("Invalid or expired verification code")
        
        # Update email_verified status
        updated_user = User(
            id=user.id,
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            created_at=user.created_at,
            email_verified=True
        )
        
        return self.user_repository.update(updated_user)

