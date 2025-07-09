# ... existing imports ...
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.message import Message
from app.utils.email import send_otp_email
from app.models.users import User
from app.database import get_db
from app.services import otp as otp_service
from app.exceptions import (
    RateLimitError,
    TokenError,
    DatabaseError,
    NotFoundError
)
from app.utils.logger import get_logger

logger = get_logger("otp_routes")

router = APIRouter()

@router.post("/request-otp", response_model=Message)
def request_otp(
    background_tasks: BackgroundTasks,
    email: str,
    purpose: str = "password_reset",
    db: Session = Depends(get_db),
):
    """
    Request OTP for various purposes (password_reset, email_verification, phone_verification, etc.)
    
    Rate limited to 5 OTPs per hour per email/purpose combination.
    """
    try:
        logger.info(f"OTP request for email: {email}, purpose: {purpose}")
        
        # Create OTP
        otp = otp_service.create_otp(db, email, purpose)
        
        # Send OTP via email
        background_tasks.add_task(
            send_otp_email,
            email_to=email,
            otp_code=otp.otp_code,
            purpose=purpose
        )
        
        logger.info(f"OTP sent successfully to {email}")
        return {"message": "OTP sent successfully"}
        
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for {email}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to send OTP to {email}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to send OTP", details={"original_error": str(e)})

@router.post("/verify-otp", response_model=Message)
def verify_otp(
    email: str,
    otp_code: str,
    purpose: str,
    db: Session = Depends(get_db)
):
    """
    Verify OTP for various purposes
    
    OTPs expire after 15 minutes and allow maximum 3 verification attempts.
    """
    try:
        logger.info(f"OTP verification attempt for email: {email}, purpose: {purpose}")
        
        is_valid = otp_service.verify_otp(db, email, otp_code, purpose)
        
        if not is_valid:
            logger.warning(f"OTP verification failed for email: {email}")
            raise TokenError("Invalid or expired OTP")
        
        # Mark email as verified if purpose is email_verification
        if purpose == "email_verification":
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.is_email_verified = True
                db.commit()
                logger.info(f"Email verified successfully for: {email}")
        
        logger.info(f"OTP verified successfully for email: {email}")
        return {"message": "OTP verified successfully"}
        
    except TokenError:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed for {email}: {str(e)}", exc_info=True)
        raise DatabaseError("OTP verification failed", details={"original_error": str(e)})

@router.get("/otp-status/{email}/{purpose}")
def get_otp_status(
    email: str,
    purpose: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of the most recent OTP for an email and purpose
    
    Returns information about whether an OTP exists, if it's used/expired,
    and how many attempts remain.
    """
    try:
        logger.info(f"OTP status check for email: {email}, purpose: {purpose}")
        
        status = otp_service.get_otp_status(db, email, purpose)
        
        return {
            "email": email,
            "purpose": purpose,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get OTP status for {email}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get OTP status", details={"original_error": str(e)})

@router.post("/cleanup-otps")
def cleanup_otps(db: Session = Depends(get_db)):
    """
    Clean up expired and old used OTPs
    
    This endpoint can be called by a scheduled task or admin.
    """
    try:
        logger.info("Starting OTP cleanup")
        
        expired_count = otp_service.cleanup_expired_otps(db)
        used_count = otp_service.cleanup_used_otps(db)
        
        logger.info(f"OTP cleanup completed: {expired_count} expired, {used_count} used OTPs removed")
        
        return {
            "message": "OTP cleanup completed",
            "expired_removed": expired_count,
            "used_removed": used_count
        }
        
    except Exception as e:
        logger.error(f"OTP cleanup failed: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to cleanup OTPs", details={"original_error": str(e)})