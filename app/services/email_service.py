"""
Email service for sending verification and password reset emails.
Supports both SMTP and SendGrid backends.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class EmailService:
    """Email service with multiple backend support."""
    
    def __init__(self):
        self.smtp_enabled = bool(os.getenv("SMTP_HOST"))
        self.sendgrid_enabled = bool(os.getenv("SENDGRID_API_KEY"))
        self.from_email = os.getenv("EMAIL_FROM", "noreply@robovai.com")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "RoboVAI")
        
    async def send_verification_email(
        self,
        to_email: str,
        verification_url: str,
        user_name: str,
    ) -> bool:
        """Send email verification link."""
        subject = "تفعيل حسابك - RoboVAI"
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Cairo, Arial, sans-serif; background: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #0891b2; margin-bottom: 20px;">مرحباً {user_name} 👋</h1>
                <p style="color: #1f2937; font-size: 16px; line-height: 1.6;">
                    شكراً لتسجيلك في منصة RoboVAI! لتفعيل حسابك، يرجى الضغط على الزر أدناه:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #0891b2, #6366f1); 
                              color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                        تفعيل الحساب الآن
                    </a>
                </div>
                <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                    أو انسخ هذا الرابط في المتصفح:<br>
                    <a href="{verification_url}" style="color: #0891b2; word-break: break-all;">{verification_url}</a>
                </p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                    إذا لم تقم بإنشاء هذا الحساب، يمكنك تجاهل هذه الرسالة.<br>
                    © 2025 RoboVAI Solutions - منصة الشات بوت الذكي
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(to_email, subject, html_content)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_url: str,
        user_name: str,
    ) -> bool:
        """Send password reset link."""
        subject = "إعادة تعيين كلمة المرور - RoboVAI"
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Cairo, Arial, sans-serif; background: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #dc2626; margin-bottom: 20px;">🔐 إعادة تعيين كلمة المرور</h1>
                <p style="color: #1f2937; font-size: 16px; line-height: 1.6;">
                    مرحباً {user_name},<br><br>
                    لقد تلقينا طلباً لإعادة تعيين كلمة مرورك. اضغط على الزر أدناه لإنشاء كلمة مرور جديدة:
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #dc2626, #ea580c); 
                              color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                        إعادة تعيين كلمة المرور
                    </a>
                </div>
                <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                    أو انسخ هذا الرابط في المتصفح:<br>
                    <a href="{reset_url}" style="color: #dc2626; word-break: break-all;">{reset_url}</a>
                </p>
                <p style="color: #dc2626; font-size: 14px; background: #fef2f2; padding: 12px; border-radius: 6px; margin-top: 20px;">
                    ⚠️ هذا الرابط صالح لمدة ساعة واحدة فقط.
                </p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                    إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذه الرسالة.<br>
                    © 2025 RoboVAI Solutions - منصة الشات بوت الذكي
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(to_email, subject, html_content)
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send email using available backend."""
        
        # Try SendGrid first (preferred)
        if self.sendgrid_enabled:
            return await self._send_via_sendgrid(to_email, subject, html_content)
        
        # Fallback to SMTP
        if self.smtp_enabled:
            return await self._send_via_smtp(to_email, subject, html_content)
        
        # No email backend configured - log for development
        logger.warning(
            f"[DEV] Email would be sent to {to_email}\n"
            f"Subject: {subject}\n"
            f"Configure SMTP_HOST or SENDGRID_API_KEY to enable emails."
        )
        return False
    
    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send email via SendGrid API."""
        api_key = os.getenv("SENDGRID_API_KEY")
        url = "https://api.sendgrid.com/v3/mail/send"
        
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}],
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                logger.info(f"✅ Email sent to {to_email} via SendGrid")
                return True
        except Exception as e:
            logger.error(f"❌ SendGrid error: {e}")
            return False
    
    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send email via SMTP (requires aiosmtplib)."""
        # TODO: Implement SMTP sending with aiosmtplib
        # For now, just log
        logger.info(f"[SMTP] Would send email to {to_email}")
        return False


# Global email service instance
email_service = EmailService()
