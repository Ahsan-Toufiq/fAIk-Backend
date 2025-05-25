from datetime import datetime
from sqlalchemy.orm import Session

from app.models.otp import OTP
from app.utils import otp as otp_utils
from app.utils import email

def create_otp(
    db: Session,
    email: str,
    purpose: str,
    length: int = 6,
    expires_minutes: int = 15
) -> OTP:
    # Invalidate any existing OTPs for this email/purpose
    db.query(OTP).filter(
        OTP.email == email,
        OTP.purpose == purpose
    ).delete()
    
    # Create new OTP
    otp_code = otp_utils.generate_otp(length)
    expires_at = otp_utils.get_otp_expiration(expires_minutes)
    
    db_otp = OTP(
        email=email,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    return db_otp

def verify_otp(
    db: Session,
    email: str,
    otp_code: str,
    purpose: str
) -> bool:
    otp = db.query(OTP).filter(
        OTP.email == email,
        OTP.otp_code == otp_code,
        OTP.purpose == purpose
    ).first()
    
    if not otp:
        return False
    
    if datetime.utcnow() > otp.expires_at:
        return False
    
    # OTP is valid - delete it
    db.delete(otp)
    db.commit()
    return True