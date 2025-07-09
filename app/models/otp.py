from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, nullable=False)  # "password_reset", "email_verification", "phone_verification", etc.
    is_used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)  # Track verification attempts
    max_attempts = Column(Integer, default=3, nullable=False)  # Maximum allowed attempts
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)  # When OTP was successfully used

    def __repr__(self):
        return f"<OTP {self.email} {self.purpose} {'USED' if self.is_used else 'ACTIVE'}>"
    
    def is_expired(self) -> bool:
        """Check if OTP is expired"""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def is_max_attempts_exceeded(self) -> bool:
        """Check if maximum attempts exceeded"""
        return self.attempts >= self.max_attempts
    
    def increment_attempts(self):
        """Increment the attempt counter"""
        self.attempts += 1
    
    def mark_as_used(self):
        """Mark OTP as used"""
        from datetime import datetime
        self.is_used = True
        self.used_at = datetime.utcnow()