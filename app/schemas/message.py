from pydantic import BaseModel

class Message(BaseModel):
    """Generic message response schema"""
    message: str

class TokenMessage(Message):
    """Message response that includes a token"""
    token: str

class OTPMessage(Message):
    """Message response that includes OTP details"""
    otp_code: str
    expires_in_minutes: int