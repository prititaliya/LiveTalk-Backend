"""
Verify Email Use Case

Use case for verifying user email with OTP code.
"""
from typing import Dict
from application.services.auth_service import AuthService
from application.services.otp_service import OTPService


class VerifyEmailUseCase:
    """Use case for verifying user email"""
    
    def __init__(self, auth_service: AuthService, otp_service: OTPService):
        """
        Initialize use case.
        
        Args:
            auth_service: Authentication service
            otp_service: OTP service
        """
        self.auth_service = auth_service
        self.otp_service = otp_service
    
    def execute(self, user_id: str, otp: str) -> Dict:
        """
        Execute email verification.
        
        Args:
            user_id: The user ID
            otp: OTP verification code
            
        Returns:
            Dictionary with updated user information
            
        Raises:
            ValueError: If verification fails (invalid/expired OTP)
        """
        # Get user to get email for OTP verification
        user = self.auth_service.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify email with OTP
        verified_user = self.auth_service.verify_email(user_id, otp, self.otp_service, user.email)
        
        return {
            "user_id": verified_user.id,
            "email": verified_user.email,
            "username": verified_user.username,
            "email_verified": verified_user.email_verified,
            "created_at": verified_user.created_at.isoformat()
        }

