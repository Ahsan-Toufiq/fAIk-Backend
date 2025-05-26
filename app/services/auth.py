from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.schemas.users import  UserCreate
from app import utils
from app.models.users import User  # Direct import from the module
from app.config import settings
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not utils.security.verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = utils.security.decode_access_token(token)
        if payload is None:
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def create_user(db: Session, user: UserCreate) -> User:
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = utils.security.get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=True,
        is_verified=False,  # legacy field
        is_email_verified=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate and send OTP for email verification
    from app.services import otp as otp_service
    from app.utils.email import send_email
    otp = otp_service.create_otp(db, user.email, purpose="email_verification")
    send_email(
        email_to=user.email,
        subject="Verify your email",
        template_name=f"Your verification OTP is: {otp.otp_code}",
        environment={}
    )
    return db_user


def verify_email(db: Session, token: str) -> User:
    email = utils.security.verify_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    db.refresh(user)
    return user

def request_password_reset(db: Session, email: str) -> bool:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False  # Don't reveal if user exists or not
    
    reset_token = utils.security.generate_password_reset_token(email)
    user.reset_password_token = reset_token
    user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    utils.email.send_password_reset_email(email=email, token=reset_token)
    return True

def reset_password(db: Session, token: str, new_password: str) -> User:
    email = utils.security.verify_password_reset_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.reset_password_token != token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    if datetime.utcnow() > user.reset_password_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expired"
        )
    
    user.hashed_password = utils.security.get_password_hash(new_password)
    user.reset_password_token = None
    user.reset_password_token_expires = None
    db.commit()
    db.refresh(user)
    return user