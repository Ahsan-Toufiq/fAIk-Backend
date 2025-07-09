from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.users import UserCreate
from app import utils
from app.models.users import User
from app.config import settings
from app.database import get_db
from app.exceptions import (
    AuthenticationError, 
    NotFoundError, 
    ConflictError, 
    TokenError,
    DatabaseError,
    handle_database_error
)
from app.utils.logger import get_logger

logger = get_logger("auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user with email and password
    
    Args:
        db: Database session
        email: User email
        password: User password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Authentication failed: User not found for email {email}")
            return None
        if not utils.security.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for email {email}")
            return None
        logger.info(f"User authenticated successfully: {email}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Database error during authentication: {str(e)}", exc_info=True)
        raise handle_database_error(e, "user authentication")
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
        raise DatabaseError("Authentication failed", details={"original_error": str(e)})

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get current user from JWT token
    
    Args:
        db: Database session
        token: JWT token
        
    Returns:
        User object
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        payload = utils.security.decode_access_token(token)
        if payload is None:
            logger.warning("Invalid token: Could not decode token")
            raise AuthenticationError("Could not validate credentials")
        
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Invalid token: No email in payload")
            raise AuthenticationError("Could not validate credentials")
    except JWTError as e:
        logger.warning(f"JWT error: {str(e)}")
        raise AuthenticationError("Could not validate credentials")
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {str(e)}", exc_info=True)
        raise AuthenticationError("Could not validate credentials")
    
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            logger.warning(f"User not found for email: {email}")
            raise AuthenticationError("Could not validate credentials")
        logger.info(f"Current user retrieved: {email}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Database error during user retrieval: {str(e)}", exc_info=True)
        raise handle_database_error(e, "get current user")
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during user retrieval: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get current user", details={"original_error": str(e)})

def create_user(db: Session, user: UserCreate) -> User:
    """
    Create new user
    
    Args:
        db: Database session
        user: User creation data
        
    Returns:
        Created user object
        
    Raises:
        ConflictError: If user already exists
        DatabaseError: If database operation fails
    """
    try:
        # Check if user already exists
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            logger.warning(f"User creation failed: Email already registered {user.email}")
            raise ConflictError("Email already registered")
        
        # Create new user
        hashed_password = utils.security.get_password_hash(user.password)
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            is_active=True,
            is_verified=False,  # legacy field
            is_email_verified=False
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User created successfully: {user.email}")

        # Generate and send OTP for email verification
        try:
            from app.services import otp as otp_service
            from app.utils.email import send_otp_email
            
            otp = otp_service.create_otp(db, user.email, purpose="email_verification")
            send_otp_email(
                email_to=user.email,
                otp_code=otp.otp_code,
                purpose="email_verification"
            )
            logger.info(f"Verification OTP sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification OTP to {user.email}: {str(e)}", exc_info=True)
            # Don't fail user creation if email fails
        
        return db_user
    except ConflictError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during user creation: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "create user")
    except Exception as e:
        logger.error(f"Unexpected error during user creation: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to create user", details={"original_error": str(e)})

def verify_email(db: Session, token: str) -> User:
    """
    Verify user email using verification token
    
    Args:
        db: Database session
        token: Verification token
        
    Returns:
        Updated user object
        
    Raises:
        TokenError: If token is invalid or expired
        NotFoundError: If user not found
        ConflictError: If email already verified
    """
    try:
        email = utils.security.verify_verification_token(token)
        if not email:
            logger.warning("Email verification failed: Invalid or expired token")
            raise TokenError("Invalid or expired verification token")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Email verification failed: User not found for email {email}")
            raise NotFoundError("User not found")
        if user.is_verified:
            logger.warning(f"Email verification failed: Email already verified for {email}")
            raise ConflictError("Email already verified")
        
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        db.commit()
        db.refresh(user)
        
        logger.info(f"Email verified successfully: {email}")
        return user
    except (TokenError, NotFoundError, ConflictError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during email verification: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "verify email")
    except Exception as e:
        logger.error(f"Unexpected error during email verification: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to verify email", details={"original_error": str(e)})

def request_password_reset(db: Session, email: str) -> bool:
    """
    Request password reset for user
    
    Args:
        db: Database session
        email: User email
        
    Returns:
        bool: True if reset token generated successfully
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Password reset requested for non-existent email: {email}")
            return False  # Don't reveal if user exists or not
        
        reset_token = utils.security.generate_password_reset_token(email)
        user.reset_password_token = reset_token
        user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        try:
            utils.email.send_password_reset_email(email=email, token=reset_token)
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}", exc_info=True)
            # Don't fail the operation if email fails
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error during password reset request: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "request password reset")
    except Exception as e:
        logger.error(f"Unexpected error during password reset request: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to request password reset", details={"original_error": str(e)})

def reset_password(db: Session, token: str, new_password: str) -> User:
    """
    Reset user password using reset token
    
    Args:
        db: Database session
        token: Password reset token
        new_password: New password
        
    Returns:
        Updated user object
        
    Raises:
        TokenError: If token is invalid or expired
        NotFoundError: If user not found
    """
    try:
        email = utils.security.verify_password_reset_token(token)
        if not email:
            logger.warning("Password reset failed: Invalid or expired token")
            raise TokenError("Invalid or expired token")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Password reset failed: User not found for email {email}")
            raise NotFoundError("User not found")
        
        if user.reset_password_token != token:
            logger.warning(f"Password reset failed: Invalid token for user {email}")
            raise TokenError("Invalid token")
        
        if datetime.utcnow() > user.reset_password_token_expires:
            logger.warning(f"Password reset failed: Token expired for user {email}")
            raise TokenError("Token expired")
        
        user.hashed_password = utils.security.get_password_hash(new_password)
        user.reset_password_token = None
        user.reset_password_token_expires = None
        db.commit()
        db.refresh(user)
        
        logger.info(f"Password reset successfully for user {email}")
        return user
    except (TokenError, NotFoundError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during password reset: {str(e)}", exc_info=True)
        db.rollback()
        raise handle_database_error(e, "reset password")
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to reset password", details={"original_error": str(e)})