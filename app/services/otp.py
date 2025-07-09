import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.otp import OTP
from app.exceptions import DatabaseError, TokenError, RateLimitError, handle_database_error
from app.utils.logger import get_logger

logger = get_logger("otp")

def generate_otp(length: int = 6) -> str:
    """
    Generate a random OTP code
    
    Args:
        length: Length of the OTP code
        
    Returns:
        str: Generated OTP code
    """
    return ''.join(random.choices(string.digits, k=length))

def check_rate_limit(db: Session, email: str, purpose: str, max_otps_per_hour: int = 5) -> bool:
    """
    Check if user has exceeded rate limit for OTP requests
    
    Args:
        db: Database session
        email: User email
        purpose: OTP purpose
        max_otps_per_hour: Maximum OTPs allowed per hour
        
    Returns:
        bool: True if rate limit not exceeded, False otherwise
    """
    try:
        # Count OTPs created in the last hour for this email and purpose
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_otps = db.query(OTP).filter(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.created_at >= one_hour_ago
        ).count()
        
        return recent_otps < max_otps_per_hour
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}", exc_info=True)
        # Allow the request if we can't check rate limit
        return True

def create_otp(db: Session, email: str, purpose: str, expiry_minutes: int = 15) -> OTP:
    """
    Create a new OTP for the given email and purpose
    
    Args:
        db: Database session
        email: User email
        purpose: Purpose of the OTP
        expiry_minutes: Minutes until OTP expires
        
    Returns:
        OTP object
        
    Raises:
        RateLimitError: If rate limit exceeded
        DatabaseError: If database operation fails
    """
    try:
        # Check rate limit
        if not check_rate_limit(db, email, purpose):
            logger.warning(f"Rate limit exceeded for email: {email}, purpose: {purpose}")
            raise RateLimitError(
                "Too many OTP requests. Please wait before requesting another OTP.",
                details={"email": email, "purpose": purpose}
            )
        
        # Delete any existing active OTPs for this email and purpose
        db.query(OTP).filter(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.is_used == False
        ).delete()
        
        # Generate new OTP
        otp_code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Create new OTP record
        otp = OTP(
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
            max_attempts=3
        )
        
        db.add(otp)
        db.commit()
        db.refresh(otp)
        
        logger.info(f"OTP created successfully for email: {email}, purpose: {purpose}")
        return otp
    except RateLimitError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during OTP creation: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "create OTP")
    except Exception as e:
        logger.error(f"Unexpected error during OTP creation: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to create OTP", details={"original_error": str(e)})

def verify_otp(db: Session, email: str, otp_code: str, purpose: str) -> bool:
    """
    Verify OTP for the given email and purpose
    
    Args:
        db: Database session
        email: User email
        otp_code: OTP code to verify
        purpose: Purpose of the OTP
        
    Returns:
        bool: True if OTP is valid, False otherwise
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        # Find the OTP record
        otp = db.query(OTP).filter(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.otp_code == otp_code,
            OTP.is_used == False
        ).first()
        
        if not otp:
            logger.warning(f"OTP verification failed: No valid OTP found for email {email}, purpose {purpose}")
            return False
        
        # Check if OTP is expired
        if otp.is_expired():
            logger.warning(f"OTP verification failed: OTP expired for email {email}")
            # Delete expired OTP
            db.delete(otp)
            db.commit()
            return False
        
        # Check if max attempts exceeded
        if otp.is_max_attempts_exceeded():
            logger.warning(f"OTP verification failed: Max attempts exceeded for email {email}")
            # Delete OTP with exceeded attempts
            db.delete(otp)
            db.commit()
            return False
        
        # Increment attempts
        otp.increment_attempts()
        
        # Check if this attempt is correct
        if otp.otp_code == otp_code:
            # Mark OTP as used
            otp.mark_as_used()
            db.commit()
            logger.info(f"OTP verified successfully for email: {email}, purpose: {purpose}")
            return True
        else:
            # Wrong OTP code
            db.commit()
            logger.warning(f"OTP verification failed: Wrong code for email {email}")
            return False
            
    except SQLAlchemyError as e:
        logger.error(f"Database error during OTP verification: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "verify OTP")
    except Exception as e:
        logger.error(f"Unexpected error during OTP verification: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to verify OTP", details={"original_error": str(e)})

def get_otp_status(db: Session, email: str, purpose: str) -> dict:
    """
    Get the status of the most recent OTP for an email and purpose
    
    Args:
        db: Database session
        email: User email
        purpose: OTP purpose
        
    Returns:
        dict: OTP status information
    """
    try:
        otp = db.query(OTP).filter(
            OTP.email == email,
            OTP.purpose == purpose
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return {
                "exists": False,
                "is_used": False,
                "is_expired": False,
                "attempts_remaining": 0
            }
        
        return {
            "exists": True,
            "is_used": otp.is_used,
            "is_expired": otp.is_expired(),
            "attempts_remaining": max(0, otp.max_attempts - otp.attempts),
            "expires_at": otp.expires_at.isoformat() if otp.expires_at else None
        }
    except Exception as e:
        logger.error(f"Error getting OTP status: {str(e)}", exc_info=True)
        return {
            "exists": False,
            "is_used": False,
            "is_expired": False,
            "attempts_remaining": 0
        }

def cleanup_expired_otps(db: Session) -> int:
    """
    Clean up expired OTPs from the database
    
    Args:
        db: Database session
        
    Returns:
        int: Number of expired OTPs deleted
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        expired_count = db.query(OTP).filter(
            OTP.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired OTPs")
        
        return expired_count
    except SQLAlchemyError as e:
        logger.error(f"Database error during OTP cleanup: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "cleanup expired OTPs")
    except Exception as e:
        logger.error(f"Unexpected error during OTP cleanup: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to cleanup expired OTPs", details={"original_error": str(e)})

def cleanup_used_otps(db: Session, days_old: int = 7) -> int:
    """
    Clean up used OTPs older than specified days
    
    Args:
        db: Database session
        days_old: Number of days old OTPs to delete
        
    Returns:
        int: Number of used OTPs deleted
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        used_count = db.query(OTP).filter(
            OTP.is_used == True,
            OTP.used_at < cutoff_date
        ).delete()
        
        db.commit()
        
        if used_count > 0:
            logger.info(f"Cleaned up {used_count} used OTPs older than {days_old} days")
        
        return used_count
    except Exception as e:
        logger.error(f"Error cleaning up used OTPs: {str(e)}", exc_info=True)
        db.rollback()
        return 0