"""
Authentication Routes

Routes for user authentication (register, login).
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from presentation.dto.requests import (
    RegisterRequest, 
    LoginRequest, 
    UpdateEmailRequest, 
    UpdateUsernameRequest, 
    UpdatePasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest
)
from presentation.dto.responses import RegisterResponse, LoginResponse, UserResponse, ResendVerificationResponse
from presentation.middleware.auth_middleware import get_current_user_id
from application.use_cases.register_user import RegisterUserUseCase
from application.use_cases.login_user import LoginUserUseCase
from application.use_cases.get_current_user import GetCurrentUserUseCase
from application.use_cases.update_user_email import UpdateUserEmailUseCase
from application.use_cases.update_user_username import UpdateUserUsernameUseCase
from application.use_cases.update_user_password import UpdateUserPasswordUseCase
from application.use_cases.verify_email import VerifyEmailUseCase
from application.use_cases.resend_verification_email import ResendVerificationEmailUseCase
from infrastructure.database.database import get_db
from core.dependency_injection import DIContainer

router = APIRouter()


def create_auth_router(container: DIContainer) -> APIRouter:
    """
    Create authentication router with dependencies.
    
    Args:
        register_user_use_case: Use case for user registration
        login_user_use_case: Use case for user login
        
    Returns:
        Configured APIRouter
    """
    @router.post("/api/auth/register", response_model=RegisterResponse)
    async def register(request: RegisterRequest, db: Session = Depends(get_db)):
        """Register a new user and send verification email"""
        try:
            register_use_case = container.register_user_use_case(db)
            result = register_use_case.execute(
                email=request.email,
                username=request.username,
                password=request.password
            )
            
            # Send verification email with OTP
            try:
                otp_service = container.otp_service()
                email_service = container.email_service()
                otp_code = otp_service.generate_otp()
                otp_service.store_otp(result["email"], otp_code, expiry_seconds=600)
                email_sent = email_service.send_verification_email(result["email"], otp_code)
                if not email_sent:
                    logger.error(f"Failed to send verification email to {result['email']}. Email service returned False.")
                else:
                    logger.info(f"Verification email sent successfully to {result['email']}")
            except Exception as email_error:
                # Log error but don't fail registration - email can be resent later
                logger.error(f"Failed to send verification email to {result.get('email', 'unknown')}: {str(email_error)}", exc_info=True)
            
            return RegisterResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to register user: {str(e)}"
            )
    
    @router.post("/api/auth/login", response_model=LoginResponse)
    async def login(request: LoginRequest, db: Session = Depends(get_db)):
        """Login user and get access token"""
        try:
            login_use_case = container.login_user_use_case(db)
            result = login_use_case.execute(
                email_or_username=request.email_or_username,
                password=request.password
            )
            
            if result is None:
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email/username or password"
                )
            
            return LoginResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to login: {str(e)}"
            )
    
    @router.get("/api/auth/me", response_model=UserResponse)
    async def get_current_user(
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Get current authenticated user information"""
        try:
            user_repository = container.user_repository(db)
            get_user_use_case = GetCurrentUserUseCase(user_repository)
            result = get_user_use_case.execute(user_id)
            
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            
            return UserResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get user: {str(e)}"
            )
    
    @router.patch("/api/auth/me/email", response_model=UserResponse)
    async def update_email(
        request: UpdateEmailRequest,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Update user email and send verification email"""
        try:
            auth_service = container.auth_service(db)
            update_email_use_case = UpdateUserEmailUseCase(auth_service)
            result = update_email_use_case.execute(user_id, request.new_email)
            
            # Send verification email with OTP for new email
            try:
                otp_service = container.otp_service()
                email_service = container.email_service()
                otp_code = otp_service.generate_otp()
                otp_service.store_otp(result["email"], otp_code, expiry_seconds=600)
                email_sent = email_service.send_verification_email(result["email"], otp_code)
                if not email_sent:
                    logger.error(f"Failed to send verification email to {result['email']}. Email service returned False.")
                else:
                    logger.info(f"Verification email sent successfully to {result['email']}")
            except Exception as email_error:
                # Log error but don't fail email update - email can be resent later
                logger.error(f"Failed to send verification email to {result.get('email', 'unknown')}: {str(email_error)}", exc_info=True)
            
            return UserResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update email: {str(e)}"
            )
    
    @router.patch("/api/auth/me/username", response_model=UserResponse)
    async def update_username(
        request: UpdateUsernameRequest,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Update user username"""
        try:
            auth_service = container.auth_service(db)
            update_username_use_case = UpdateUserUsernameUseCase(auth_service)
            result = update_username_use_case.execute(user_id, request.new_username)
            return UserResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update username: {str(e)}"
            )
    
    @router.patch("/api/auth/me/password", response_model=UserResponse)
    async def update_password(
        request: UpdatePasswordRequest,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Update user password"""
        try:
            auth_service = container.auth_service(db)
            update_password_use_case = UpdateUserPasswordUseCase(auth_service)
            result = update_password_use_case.execute(
                user_id, 
                request.current_password, 
                request.new_password
            )
            return UserResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update password: {str(e)}"
            )
    
    @router.post("/api/auth/verify-email", response_model=UserResponse)
    async def verify_email(
        request: VerifyEmailRequest,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Verify user email with OTP code"""
        try:
            auth_service = container.auth_service(db)
            otp_service = container.otp_service()
            verify_email_use_case = VerifyEmailUseCase(auth_service, otp_service)
            result = verify_email_use_case.execute(user_id, request.otp)
            return UserResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to verify email: {str(e)}"
            )
    
    @router.post("/api/auth/resend-verification", response_model=ResendVerificationResponse)
    async def resend_verification(
        request: ResendVerificationRequest = None,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
    ):
        """Resend verification email with new OTP"""
        try:
            user_repository = container.user_repository(db)
            otp_service = container.otp_service()
            email_service = container.email_service()
            resend_use_case = ResendVerificationEmailUseCase(user_repository, otp_service, email_service)
            result = resend_use_case.execute(user_id)
            return ResendVerificationResponse(**result)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to resend verification email: {str(e)}"
            )
    
    return router

