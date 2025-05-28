import emails
from emails.template import JinjaTemplate
from datetime import datetime, timedelta
import jwt
import os
from app.config import settings

def send_email(
    email_to: str,
    subject: str = "",
    html_content: str = None,
    template_name: str = None,
    environment: dict = {},
) -> bool:
    """Send email with either direct HTML content or a template"""
    # Check required email settings
    required_settings = [
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.EMAILS_FROM
    ]
    
    if not all(required_settings):
        print("Email configuration not set - skipping email sending")
        return False

    # Create message
    if html_content:
        message = emails.Message(
            mail_from=settings.EMAILS_FROM,
            subject=subject,
            html=html_content,
        )
    elif template_name:
        message = emails.Message(
            mail_from=settings.EMAILS_FROM,
            subject=subject,
            html=JinjaTemplate(template_name).render(**environment),
        )
    else:
        raise ValueError("Either html_content or template_name must be provided")

    # Configure SMTP options
    smtp_options = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "user": settings.SMTP_USER,
        "password": settings.SMTP_PASSWORD,
    }
    
    # Add TLS/SSL configuration if specified
    if hasattr(settings, 'SMTP_TLS') and settings.SMTP_TLS:
        smtp_options["tls"] = True
    if hasattr(settings, 'SMTP_SSL') and settings.SMTP_SSL:
        smtp_options["ssl"] = True
    
    # Send email
    try:
        response = message.send(to=email_to, smtp=smtp_options)
        return response.success
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def send_verification_email(email: str, token: str):
    subject = "Verify your email address"
    template = """
    <html>
    <body>
        <p>Hi,</p>
        <p>Please verify your email address by clicking the link below:</p>
        <a href="{{ verification_url }}">Verify Email</a>
        <p>This link will expire in 24 hours.</p>
    </body>
    </html>
    """
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    return send_email(
        email_to=email,
        subject=subject,
        template_name=template,
        environment={"verification_url": verification_url},
    )

def send_password_reset_email(email: str, token: str):
    subject = "Password Reset Request"
    template = """
    <html>
    <body>
        <p>Hi,</p>
        <p>You requested a password reset. Click the link below to reset your password:</p>
        <a href="{{ reset_url }}">Reset Password</a>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, please ignore this email.</p>
    </body>
    </html>
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    return send_email(
        email_to=email,
        subject=subject,
        template_name=template,
        environment={"reset_url": reset_url},
    )