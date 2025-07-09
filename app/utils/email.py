import emails
from emails.template import JinjaTemplate
from datetime import datetime, timedelta
import jwt
import os
from app.config import settings
from app.utils.logger import get_logger
from app.exceptions import EmailError, handle_email_error

logger = get_logger("email")

def send_email(
    email_to: str,
    subject: str = "",
    html_content: str = None,
    template_name: str = None,
    environment: dict = {},
) -> bool:
    """
    Send email with either direct HTML content or a template
    
    Args:
        email_to: Recipient email address
        subject: Email subject
        html_content: Direct HTML content
        template_name: Template string to render
        environment: Template variables
        
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Raises:
        EmailError: If email configuration is missing or sending fails
    """
    # Check required email settings
    required_settings = [
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.EMAILS_FROM
    ]
    
    if not all(required_settings):
        error_msg = "Email configuration not set - skipping email sending"
        logger.warning(error_msg)
        raise EmailError(
            message=error_msg,
            details={
                "missing_settings": [setting for setting, value in {
                    "SMTP_HOST": settings.SMTP_HOST,
                    "SMTP_PORT": settings.SMTP_PORT,
                    "SMTP_USER": settings.SMTP_USER,
                    "SMTP_PASSWORD": settings.SMTP_PASSWORD,
                    "EMAILS_FROM": settings.EMAILS_FROM
                }.items() if not value]
            }
        )

    # Create message
    try:
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
    except Exception as e:
        logger.error(f"Failed to create email message: {str(e)}", exc_info=True)
        raise handle_email_error(e, "create email message")

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
        logger.info(f"Sending email to {email_to} with subject: {subject}")
        response = message.send(to=email_to, smtp=smtp_options)
        
        if response.success:
            logger.info(f"Email sent successfully to {email_to}")
            return True
        else:
            logger.error(f"Failed to send email to {email_to}: {response.error}")
            raise EmailError(
                message=f"Failed to send email: {response.error}",
                details={"recipient": email_to, "subject": subject}
            )
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {str(e)}", exc_info=True)
        raise handle_email_error(e, "send email")


def send_verification_email(email: str, token: str) -> bool:
    """
    Send email verification email
    
    Args:
        email: Recipient email address
        token: Verification token
        
    Returns:
        bool: True if email sent successfully
        
    Raises:
        EmailError: If email sending fails
    """
    try:
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
        
        logger.info(f"Sending verification email to {email}")
        return send_email(
            email_to=email,
            subject=subject,
            template_name=template,
            environment={"verification_url": verification_url},
        )
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}", exc_info=True)
        raise handle_email_error(e, "send verification email")


def send_password_reset_email(email: str, token: str) -> bool:
    """
    Send password reset email
    
    Args:
        email: Recipient email address
        token: Password reset token
        
    Returns:
        bool: True if email sent successfully
        
    Raises:
        EmailError: If email sending fails
    """
    try:
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
        
        logger.info(f"Sending password reset email to {email}")
        return send_email(
            email_to=email,
            subject=subject,
            template_name=template,
            environment={"reset_url": reset_url},
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}", exc_info=True)
        raise handle_email_error(e, "send password reset email")


def send_otp_email(email: str, otp_code: str, purpose: str = "verification") -> bool:
    """
    Send OTP email
    
    Args:
        email: Recipient email address
        otp_code: OTP code
        purpose: Purpose of the OTP (verification, password_reset, etc.)
        
    Returns:
        bool: True if email sent successfully
        
    Raises:
        EmailError: If email sending fails
    """
    try:
        subject = f"Your {purpose.replace('_', ' ').title()} OTP"
        template = f"""
        <html>
        <body>
            <p>Your OTP for {purpose.replace('_', ' ')} is: <strong>{{ otp_code }}</strong></p>
            <p>This OTP will expire in 15 minutes.</p>
        </body>
        </html>
        """
        
        logger.info(f"Sending OTP email to {email} for purpose: {purpose}")
        return send_email(
            email_to=email,
            subject=subject,
            template_name=template,
            environment={"otp_code": otp_code},
        )
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}", exc_info=True)
        raise handle_email_error(e, "send OTP email")