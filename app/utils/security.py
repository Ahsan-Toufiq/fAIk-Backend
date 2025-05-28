from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Adjust rounds as needed (default is 12)
    bcrypt__ident="2b"  # Use the modern bcrypt variant
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
    
def generate_verification_token(email: str) -> str:
    expires_delta = timedelta(hours=24)
    return create_access_token(
        data={"sub": email, "purpose": "email_verification"},
        expires_delta=expires_delta
    )

def verify_verification_token(token: str) -> Optional[str]:
    payload = decode_access_token(token)
    if not payload:
        return None
    if payload.get("purpose") != "email_verification":
        return None
    return payload.get("sub")

def generate_password_reset_token(email: str) -> str:
    expires_delta = timedelta(hours=1)
    return create_access_token(
        data={"sub": email, "purpose": "password_reset"},
        expires_delta=expires_delta
    )

def verify_password_reset_token(token: str) -> Optional[str]:
    payload = decode_access_token(token)
    if not payload:
        return None
    if payload.get("purpose") != "password_reset":
        return None
    return payload.get("sub")