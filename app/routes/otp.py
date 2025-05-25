# ... existing imports ...
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from app.services import otp as otp_service
from app.database import get_db  # Import get_db from the correct module
from app.models import OTP
from sqlalchemy.orm import Session
from app.schemas.message import Message
from app.utils.email import send_email
router = APIRouter()

@router.post("/request-otp", response_model=Message)
def request_otp(
    background_tasks: BackgroundTasks,
    email: str,
    purpose: str = "password_reset",
    db: Session = Depends(get_db),
):
    """
    Request OTP for various purposes (password_reset, phone_verification, etc.)
    """
    otp = otp_service.create_otp(db, email, purpose)
    
    # Send OTP via email (or SMS in a real implementation)
    if purpose == "password_reset":
        subject = "Your Password Reset OTP"
        template = f"""
        <html>
        <body>
            <p>Your OTP for password reset is: <strong>{otp.otp_code}</strong></p>
            <p>This OTP will expire in 15 minutes.</p>
        </body>
        </html>
        """
        background_tasks.add_task(
            send_email,
            email_to=email,
            subject=subject,
            template_name=template,
            environment={}
        )
    
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp", response_model=Message)
def verify_otp(
    email: str,
    otp_code: str,
    purpose: str,
    db: Session = Depends(get_db)
):
    """
    Verify OTP for various purposes
    """
    is_valid = otp_service.verify_otp(db, email, otp_code, purpose)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    return {"message": "OTP verified successfully"}