"""
Email Service

Service for sending emails using SendGrid API.
"""
import os
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SendGrid"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize email service.
        
        Args:
            api_key: SendGrid API key (reads from SENDGRID_API_KEY env if not provided)
        """
        self.api_key = api_key or os.environ.get("SENDGRID_API_KEY")
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY environment variable is required")
        
        self.sendgrid_client = SendGridAPIClient(self.api_key)
    
    def send_verification_email(self, email: str, otp_code: str, sender_email: Optional[str] = None) -> bool:
        """
        Send verification email with OTP code.
        
        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code
            sender_email: Sender email address (uses default if not provided)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Use sender email from environment or default
            from_email = sender_email or os.environ.get("SENDGRID_FROM_EMAIL", "noreply@livetalk.com")
            
            # Email subject
            subject = "Verify your email address - LiveTalk"
            
            # Email content (HTML)
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Email Verification</h2>
                    <p>Thank you for signing up for LiveTalk! Please verify your email address by entering the code below:</p>
                    <div style="background-color: #F3F4F6; border: 2px solid #4F46E5; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #4F46E5; font-size: 32px; letter-spacing: 8px; margin: 0;">{otp_code}</h1>
                    </div>
                    <p>This code will expire in 10 minutes.</p>
                    <p>If you didn't create an account with LiveTalk, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 20px 0;">
                    <p style="color: #6B7280; font-size: 12px;">This is an automated message, please do not reply to this email.</p>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            Email Verification
            
            Thank you for signing up for LiveTalk! Please verify your email address by entering the code below:
            
            Verification Code: {otp_code}
            
            This code will expire in 10 minutes.
            
            If you didn't create an account with LiveTalk, please ignore this email.
            """
            
            # Create mail message
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )
            
            # Send email
            try:
                response = self.sendgrid_client.send(message)
                
                # Check response status
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Verification email sent successfully to {email}")
                    return True
                else:
                    # Try to get error details from response
                    try:
                        error_body = response.body.decode('utf-8') if response.body else "No error body"
                    except:
                        error_body = str(response.body)
                    
                    logger.error(f"Failed to send verification email to {email}. Status code: {response.status_code}")
                    logger.error(f"Response body: {error_body}")
                    logger.error(f"Response headers: {dict(response.headers) if hasattr(response, 'headers') else 'N/A'}")
                    return False
            except Exception as send_error:
                # Handle SendGrid API exceptions
                error_msg = str(send_error)
                logger.error(f"SendGrid API error sending email to {email}: {error_msg}")
                
                # Try to get more details from the exception
                if hasattr(send_error, 'body'):
                    try:
                        error_body = send_error.body.decode('utf-8') if isinstance(send_error.body, bytes) else str(send_error.body)
                        logger.error(f"SendGrid error body: {error_body}")
                    except:
                        logger.error(f"SendGrid error body (raw): {send_error.body}")
                
                if "403" in error_msg or "Forbidden" in error_msg:
                    logger.error("⚠️  SendGrid 403 Forbidden error usually means:")
                    logger.error("   1. The sender email is not verified in SendGrid")
                    logger.error("   2. The API key doesn't have 'Mail Send' permissions")
                    logger.error(f"   Current sender email: {from_email}")
                    logger.error("   Please verify your sender email at: https://app.sendgrid.com/settings/sender_auth/senders/new")
                    logger.error("   Then set SENDGRID_FROM_EMAIL in .env.local to the verified email")
                
                return False
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error sending verification email to {email}: {error_msg}", exc_info=True)
            # Log more details for SendGrid-specific errors
            if "sender" in error_msg.lower() or "from" in error_msg.lower():
                logger.error("SendGrid requires a verified sender email. Please verify your sender email in SendGrid dashboard and set SENDGRID_FROM_EMAIL in .env.local")
            return False

