"""
Email service for sending verification and password reset emails.
Supports Gmail SMTP, generic SMTP, and SendGrid backends.

Gmail SMTP Configuration:
- Enable 2-Step Verification in your Google account
- Generate an App Password: https://myaccount.google.com/apppasswords
- Use the app password as SMTP_PASSWORD (not your Gmail password)
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
import asyncio
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service with multiple backend support.
    
    Priority order:
    1. SendGrid API (if SENDGRID_API_KEY is set)
    2. Gmail SMTP (if using smtp.gmail.com)
    3. Generic SMTP (any other SMTP server)
    """

    def __init__(self):
        self.smtp_enabled = bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)
        self.sendgrid_enabled = bool(settings.sendgrid_api_key)
        self.from_email = settings.email_from or settings.smtp_user
        self.from_name = settings.email_from_name or "RoboVAI"
        
        # Gmail specific settings
        self.is_gmail = settings.smtp_host.lower() in ['smtp.gmail.com', 'smtp.googlemail.com'] if settings.smtp_host else False
        
        # Log configuration status
        if self.sendgrid_enabled:
            logger.info("📧 Email service: SendGrid API enabled")
        elif self.smtp_enabled:
            if self.is_gmail:
                logger.info("📧 Email service: Gmail SMTP enabled")
            else:
                logger.info(f"📧 Email service: SMTP enabled ({settings.smtp_host})")
        else:
            logger.warning("⚠️ Email service: No email backend configured!")

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

        # Try SendGrid first (preferred for production)
        if self.sendgrid_enabled:
            result = await self._send_via_sendgrid(to_email, subject, html_content)
            if result:
                return True
            # Fallback to SMTP if SendGrid fails
            logger.warning("SendGrid failed, trying SMTP fallback...")

        # Try SMTP (Gmail or generic)
        if self.smtp_enabled:
            if self.is_gmail:
                return await self._send_via_gmail(to_email, subject, html_content)
            else:
                return await self._send_via_smtp(to_email, subject, html_content)

        # No email backend configured - log for development
        logger.warning(
            f"[DEV MODE] Email would be sent to {to_email}\n"
            f"Subject: {subject}\n"
            f"Configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD or SENDGRID_API_KEY to enable emails.\n"
            f"For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_TLS=true"
        )
        return False

    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send email via SendGrid API."""
        api_key = settings.sendgrid_api_key
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
        """Send email via generic SMTP server."""
        try:
            # Create MIME message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)

            def send_sync():
                """Synchronous SMTP send function."""
                smtp_host = settings.smtp_host
                smtp_port = settings.smtp_port
                
                # Determine connection type based on port
                if smtp_port == 465:
                    # SSL connection (implicit TLS)
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                        if settings.smtp_user and settings.smtp_password:
                            server.login(settings.smtp_user, settings.smtp_password)
                        server.send_message(message)
                else:
                    # Standard connection with optional STARTTLS (port 587)
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                        server.ehlo()
                        if settings.smtp_tls:
                            context = ssl.create_default_context()
                            server.starttls(context=context)
                            server.ehlo()
                        if settings.smtp_user and settings.smtp_password:
                            server.login(settings.smtp_user, settings.smtp_password)
                        server.send_message(message)

            # Run blocking SMTP call in a separate thread
            await asyncio.to_thread(send_sync)
            logger.info(f"✅ Email sent to {to_email} via SMTP ({settings.smtp_host})")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error("💡 For Gmail: Make sure you're using an App Password, not your regular password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ SMTP unexpected error: {e}")
            return False

    async def _send_via_gmail(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """
        Send email via Gmail SMTP with proper SSL/TLS handling.
        
        Gmail requires:
        - 2-Step Verification enabled on Google account
        - App Password (not regular Gmail password)
        - Port 587 with STARTTLS or Port 465 with SSL
        """
        try:
            # Create MIME message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            # Add plain text fallback
            plain_text = f"Subject: {subject}\n\nPlease view this email in an HTML-capable email client."
            plain_part = MIMEText(plain_text, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            
            message.attach(plain_part)
            message.attach(html_part)

            def send_sync():
                """Synchronous Gmail send function."""
                smtp_host = settings.smtp_host
                smtp_port = settings.smtp_port
                smtp_user = settings.smtp_user
                smtp_password = settings.smtp_password
                
                # Create secure SSL context
                context = ssl.create_default_context()
                
                # Resolve to IPv4 to avoid IPv6 routing issues on Render
                target_host = smtp_host
                try:
                    # Filter for IPv4 (AF_INET)
                    addr_info = socket.getaddrinfo(smtp_host, smtp_port, socket.AF_INET, socket.SOCK_STREAM)
                    if addr_info:
                        target_host = addr_info[0][4][0]
                        if target_host != smtp_host:
                            logger.debug(f"Resolved {smtp_host} to {target_host} (IPv4) to avoid routing issues")
                except Exception as e:
                    logger.warning(f"DNS resolution warning: {e}")

                if smtp_port == 465:
                    # Gmail SSL (implicit TLS)
                    logger.debug(f"Connecting to Gmail via SSL on port {smtp_port}")
                    # Note: For SSL port 465, we stick to hostname to ensure SSL context works automatically
                    # If IPv6 issues persist on 465, we might need a more complex fix.
                    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
                        server.login(smtp_user, smtp_password)
                        server.send_message(message)
                else:
                    # Gmail STARTTLS (explicit TLS) - Port 587
                    logger.debug(f"Connecting to Gmail via STARTTLS on port {smtp_port}")
                    
                    # Use target_host (IPv4) to bypass potential IPv6 routing issues
                    with smtplib.SMTP(target_host, smtp_port, timeout=30) as server:
                        if target_host != smtp_host:
                            # Hack: Restore original hostname for SSL verification
                            server._host = smtp_host
                        
                        server.ehlo("localhost")
                        server.starttls(context=context)
                        server.ehlo("localhost")
                        server.login(smtp_user, smtp_password)
                        server.send_message(message)

            # Run blocking SMTP call in a separate thread
            await asyncio.to_thread(send_sync)
            logger.info(f"✅ Email sent to {to_email} via Gmail SMTP")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Gmail Authentication failed: {e}")
            logger.error(
                "💡 Gmail requires an App Password:\n"
                "   1. Enable 2-Step Verification: https://myaccount.google.com/security\n"
                "   2. Generate App Password: https://myaccount.google.com/apppasswords\n"
                "   3. Use the 16-character app password as SMTP_PASSWORD"
            )
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"❌ Gmail rejected recipient {to_email}: {e}")
            return False
        except smtplib.SMTPSenderRefused as e:
            logger.error(f"❌ Gmail rejected sender {self.from_email}: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Gmail SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Gmail unexpected error: {type(e).__name__}: {e}")
            return False


# Global email service instance
email_service = EmailService()
