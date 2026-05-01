"""
Resend Verification Email Use Case

Use case for resending verification email with new OTP.
"""
from typing import Dict
from application.services.otp_service import OTPService
from infrastructure.services.email_service import EmailService
from domain.interfaces.user_repository import IUserRepository


class ResendVerificationEmailUseCase:
    """Use case for resending verification email"""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        otp_service: OTPService,
        email_service: EmailService
    ):
        """
        Initialize use case.
        
        Args:
            user_repository: User repository
            otp_service: OTP service
            email_service: Email service
        """
        self.user_repository = user_repository
        self.otp_service = otp_service
        self.email_service = email_service
    
    def execute(self, user_id: str) -> Dict:
        """
        Execute resend verification email.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with success status
            
        Raises:
            ValueError: If user not found or already verified
        """
        # Get user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Check if already verified
        if user.email_verified:
            raise ValueError("Email is already verified")
        
        # Generate new OTP
        otp_code = self.otp_service.generate_otp()
        
        # Store OTP in Redis (10 minute expiry)
        self.otp_service.store_otp(user.email, otp_code, expiry_seconds=600)
        
        # Send verification email
        email_sent = self.email_service.send_verification_email(user.email, otp_code)
        
        if not email_sent:
            raise ValueError("Failed to send verification email")
        
        return {
            "success": True,
            "message": "Verification email sent successfully"
        }

