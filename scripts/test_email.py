#!/usr/bin/env python3
"""
Email Configuration Test Script for RoboVAI

This script tests your email configuration (Gmail SMTP, generic SMTP, or SendGrid).
Run this script to verify that emails can be sent successfully.

Usage:
    python scripts/test_email.py
    python scripts/test_email.py --to your-email@example.com

For Gmail SMTP:
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Set SMTP_PASSWORD to the 16-character app password
"""

import asyncio
import sys
import os
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.email_service import EmailService

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print a nice banner."""
    print("\n" + "=" * 60)
    print("🧪 RoboVAI Email Configuration Test")
    print("=" * 60 + "\n")


def check_configuration():
    """Check and display current email configuration."""
    print("📧 Current Email Configuration:")
    print("-" * 40)
    
    # SMTP Configuration
    smtp_configured = bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)
    print(f"  SMTP Host:     {settings.smtp_host or '❌ Not set'}")
    print(f"  SMTP Port:     {settings.smtp_port}")
    print(f"  SMTP User:     {settings.smtp_user or '❌ Not set'}")
    print(f"  SMTP Password: {'✅ Set' if settings.smtp_password else '❌ Not set'}")
    print(f"  SMTP TLS:      {settings.smtp_tls}")
    print(f"  Email From:    {settings.email_from or settings.smtp_user or '❌ Not set'}")
    print(f"  Email Name:    {settings.email_from_name}")
    
    # Gmail detection
    is_gmail = settings.smtp_host.lower() in ['smtp.gmail.com', 'smtp.googlemail.com'] if settings.smtp_host else False
    if is_gmail:
        print(f"\n  🔵 Gmail detected!")
        print(f"     Make sure you're using an App Password, not your Gmail password.")
        print(f"     Generate one at: https://myaccount.google.com/apppasswords")
    
    # SendGrid
    sendgrid_configured = bool(settings.sendgrid_api_key)
    print(f"\n  SendGrid API:  {'✅ Configured' if sendgrid_configured else '❌ Not configured'}")
    
    print("-" * 40)
    
    if smtp_configured:
        print("✅ SMTP is configured")
        return True
    elif sendgrid_configured:
        print("✅ SendGrid is configured")
        return True
    else:
        print("❌ No email backend configured!")
        print("\n💡 To configure Gmail SMTP, add these to your .env file:")
        print("   SMTP_HOST=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   SMTP_USER=your-email@gmail.com")
        print("   SMTP_PASSWORD=your-16-char-app-password")
        print("   SMTP_TLS=true")
        print("   EMAIL_FROM=your-email@gmail.com")
        print("   EMAIL_FROM_NAME=RoboVAI")
        return False


async def test_email_send(to_email: str):
    """Test sending an email."""
    print(f"\n📤 Sending test email to: {to_email}")
    print("-" * 40)
    
    email_service = EmailService()
    
    # Create test email content
    html_content = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Cairo, Arial, sans-serif; background: #f3f4f6; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h1 style="color: #0891b2; margin-bottom: 20px;">✅ اختبار ناجح!</h1>
            <p style="color: #1f2937; font-size: 16px; line-height: 1.6;">
                مرحباً! 👋<br><br>
                إذا تلقيت هذه الرسالة، فإن إعدادات البريد الإلكتروني تعمل بشكل صحيح! 🎉
            </p>
            <div style="background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; color: #059669; font-weight: bold;">
                    ✓ SMTP Connection: Successful<br>
                    ✓ Authentication: Passed<br>
                    ✓ Email Delivery: Working
                </p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">
                يمكنك الآن استخدام ميزات التسجيل وإعادة تعيين كلمة المرور بأمان.
            </p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                © 2025 RoboVAI Solutions - منصة الشات بوت الذكي<br>
                تم إرسال هذه الرسالة من سكريبت الاختبار
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        success = await email_service._send_email(
            to_email=to_email,
            subject="🧪 [TEST] RoboVAI Email Configuration Test",
            html_content=html_content,
        )
        
        if success:
            print("✅ SUCCESS! Email sent successfully!")
            print(f"   Check inbox of: {to_email}")
            print("   (Also check spam/junk folder)")
            return True
        else:
            print("❌ FAILED! Email sending returned False")
            print("   Check the logs above for error details")
            return False
            
    except Exception as e:
        print(f"❌ ERROR! {type(e).__name__}: {e}")
        return False


async def test_verification_email(to_email: str):
    """Test sending a verification email (like the real registration flow)."""
    print(f"\n📧 Testing verification email flow...")
    print("-" * 40)
    
    email_service = EmailService()
    
    # Simulate verification URL
    test_url = "http://localhost:8000/ui/auth/verify-email?token=test-token-12345"
    
    try:
        success = await email_service.send_verification_email(
            to_email=to_email,
            verification_url=test_url,
            user_name="مستخدم تجريبي",
        )
        
        if success:
            print("✅ Verification email sent successfully!")
            return True
        else:
            print("❌ Verification email failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR! {type(e).__name__}: {e}")
        return False


async def test_password_reset_email(to_email: str):
    """Test sending a password reset email."""
    print(f"\n🔐 Testing password reset email flow...")
    print("-" * 40)
    
    email_service = EmailService()
    
    # Simulate reset URL
    test_url = "http://localhost:8000/ui/auth/reset-password?token=test-reset-token-12345"
    
    try:
        success = await email_service.send_password_reset_email(
            to_email=to_email,
            reset_url=test_url,
            user_name="مستخدم تجريبي",
        )
        
        if success:
            print("✅ Password reset email sent successfully!")
            return True
        else:
            print("❌ Password reset email failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR! {type(e).__name__}: {e}")
        return False


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test RoboVAI email configuration")
    parser.add_argument(
        "--to", "-t",
        type=str,
        help="Email address to send test email to",
        default=None
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all email tests (simple, verification, password reset)"
    )
    args = parser.parse_args()
    
    print_banner()
    
    # Check configuration
    if not check_configuration():
        print("\n⚠️  Please configure email settings before running tests.")
        sys.exit(1)
    
    # Get test email address
    to_email = args.to or settings.smtp_user or settings.email_from
    if not to_email:
        print("\n❌ No email address provided!")
        print("   Use: python scripts/test_email.py --to your-email@example.com")
        sys.exit(1)
    
    # Run tests
    print("\n" + "=" * 60)
    print("🚀 Running Email Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Simple email
    result1 = await test_email_send(to_email)
    results.append(("Simple Email", result1))
    
    # Test 2 & 3: If --all flag is set
    if args.all:
        result2 = await test_verification_email(to_email)
        results.append(("Verification Email", result2))
        
        result3 = await test_password_reset_email(to_email)
        results.append(("Password Reset Email", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("-" * 60)
    
    if all_passed:
        print("🎉 All tests passed! Email configuration is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Make sure BASE_URL is set correctly in .env")
        print("   2. Test the registration flow in your browser")
        print("   3. Test the password reset flow")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("\n💡 Common issues:")
        print("   - Gmail: Make sure you're using an App Password")
        print("   - Firewall: Ensure ports 587 or 465 are open")
        print("   - Credentials: Double-check SMTP_USER and SMTP_PASSWORD")
    
    print("\n" + "=" * 60 + "\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
