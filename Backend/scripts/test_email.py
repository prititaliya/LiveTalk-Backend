#!/usr/bin/env python3
"""
Test script to verify SendGrid email configuration and send a test email.

Usage:
    python scripts/test_email.py your-email@example.com
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(".env.local")

from infrastructure.services.email_service import EmailService

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_email.py recipient@example.com")
        sys.exit(1)
    
    recipient = sys.argv[1]
    
    # Check if API key is set
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("❌ ERROR: SENDGRID_API_KEY not found in environment")
        print("   Please set it in Backend/.env.local")
        sys.exit(1)
    
    # Check if sender email is set
    sender_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@livetalk.com")
    print(f"📧 Sender email: {sender_email}")
    print(f"📧 Recipient: {recipient}")
    print()
    
    try:
        email_service = EmailService()
        print("✅ EmailService initialized successfully")
        
        # Generate a test OTP
        test_otp = "123456"
        print(f"🧪 Sending test email with OTP: {test_otp}")
        print()
        
        try:
            result = email_service.send_verification_email(recipient, test_otp)
            
            if result:
                print("✅ Test email sent successfully!")
                print(f"   Please check {recipient} inbox (and spam folder)")
            else:
                print("❌ Failed to send test email")
                print()
                print("🔍 Common issues:")
                print("   1. Sender email not verified in SendGrid")
                print("      → Go to: https://app.sendgrid.com/settings/sender_auth/senders/new")
                print("      → Verify your sender email, then set SENDGRID_FROM_EMAIL in .env.local")
                print()
                print("   2. API key doesn't have 'Mail Send' permissions")
                print("      → Go to: https://app.sendgrid.com/settings/api_keys")
                print("      → Ensure your API key has 'Full Access' or at least 'Mail Send' permissions")
                print()
                print("   3. Check your SendGrid account status (may be suspended/limited)")
                print("      → Go to: https://app.sendgrid.com/settings/billing")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

