from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from fastapi import BackgroundTasks
from app.schemas.message import Message
from app.schemas.users import UserOut, UserCreate, GoogleAuth, FacebookAuth, MicrosoftAuth
from app.schemas.token import Token
from app.models.users import User
from app.database import get_db
from app.services.auth import (
    authenticate_user,
    create_user,
    get_current_user,
    verify_email,
    reset_password,
    oauth2_scheme
)
from app.services import social_auth
from app.services.microsoft_auth import microsoft_auth_service
from app.utils import security, email
from app.config import settings
from app.services import otp as otp_service
from app.models.otp import OTP
from app.exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    TokenError,
    DatabaseError,
    OAuthError,
    ValidationError
)
from app.utils.logger import get_logger

logger = get_logger("auth_routes")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create new user with email and password
    """
    try:
        logger.info(f"User signup attempt for email: {user.email}")
        result = create_user(db=db, user=user)
        logger.info(f"User signup successful for email: {user.email}")
        return result
    except (ConflictError, DatabaseError) as e:
        logger.error(f"User signup failed for email {user.email}: {str(e)}")
        raise

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    try:
        logger.info(f"Login attempt for email: {form_data.username}")
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Login failed: Invalid credentials for email {form_data.username}")
            raise AuthenticationError("Incorrect email or password")
        if not user.is_active:
            logger.warning(f"Login failed: Inactive user {form_data.username}")
            raise AuthenticationError("Inactive user")
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        logger.info(f"Login successful for email: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for {form_data.username}: {str(e)}", exc_info=True)
        raise DatabaseError("Login failed", details={"original_error": str(e)})

@router.get("/microsoft/login")
def microsoft_login():
    """
    Get Microsoft OAuth login URL
    """
    try:
        url = microsoft_auth_service.get_authorization_url()
        logger.info("Microsoft OAuth URL generated successfully")
        return {"url": url}
    except Exception as e:
        logger.error(f"Failed to generate Microsoft OAuth URL: {str(e)}", exc_info=True)
        raise OAuthError("Failed to generate Microsoft OAuth URL", details={"original_error": str(e)})

@router.post("/microsoft/callback", response_model=Token)
async def microsoft_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle Microsoft OAuth callback
    """
    try:
        logger.info("Microsoft OAuth callback received")
        user = await microsoft_auth_service.authenticate_user(db, code)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        logger.info(f"Microsoft OAuth authentication successful for user: {user.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Microsoft OAuth callback failed: {str(e)}", exc_info=True)
        raise OAuthError("Microsoft OAuth authentication failed", details={"original_error": str(e)})

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user information
    """
    logger.info(f"User profile accessed for: {current_user.email}")
    return current_user

@router.post("/verify-email", response_model=UserOut)
def verify_email_endpoint(token: str, db: Session = Depends(get_db)):
    """
    Verify user's email using the verification token
    """
    try:
        logger.info("Email verification attempt")
        result = verify_email(db=db, token=token)
        logger.info("Email verification successful")
        return result
    except (TokenError, NotFoundError, ConflictError) as e:
        logger.error(f"Email verification failed: {str(e)}")
        raise

@router.post("/resend-verification", response_model=Message)
def resend_verification(
    background_tasks: BackgroundTasks,
    email_address: str,
    db: Session = Depends(get_db),
):
    """
    Resend verification email
    """
    try:
        logger.info(f"Resend verification requested for email: {email_address}")
        user = db.query(User).filter(User.email == email_address).first()
        if not user:
            logger.warning(f"Resend verification failed: User not found for email {email_address}")
            raise NotFoundError("User not found")
        if user.is_verified:
            logger.warning(f"Resend verification failed: Email already verified for {email_address}")
            raise ConflictError("Email already verified")
        
        # Generate new token
        new_token = security.generate_verification_token(user.email)
        user.verification_token = new_token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        
        # Send email in background
        background_tasks.add_task(
            email.send_verification_email,
            email=email_address,
            token=new_token
        )
        
        logger.info(f"Verification email resent successfully to {email_address}")
        return {"message": "Verification email resent successfully"}
    except (NotFoundError, ConflictError):
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification email to {email_address}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to resend verification email", details={"original_error": str(e)})

@router.post("/forgot-password", response_model=Message)
def forgot_password(
    background_tasks: BackgroundTasks,
    email_address: str,
    db: Session = Depends(get_db),
):
    """
    Request password reset
    """
    try:
        logger.info(f"Password reset requested for email: {email_address}")
        user = db.query(User).filter(User.email == email_address).first()
        if user:
            reset_token = security.generate_password_reset_token(email_address)
            user.reset_password_token = reset_token
            user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.commit()
            
            background_tasks.add_task(
                email.send_password_reset_email,
                email=email_address,
                token=reset_token
            )
            logger.info(f"Password reset email sent to {email_address}")
        else:
            logger.info(f"Password reset requested for non-existent email: {email_address}")
        
        # Always return success to prevent email enumeration
        return {"message": "If this email exists, a password reset link has been sent"}
    except Exception as e:
        logger.error(f"Failed to process password reset for {email_address}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to process password reset", details={"original_error": str(e)})

@router.post("/reset-password", response_model=Message)
def reset_password_endpoint(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from email
    """
    try:
        logger.info("Password reset attempt")
        reset_password(db=db, token=token, new_password=new_password)
        logger.info("Password reset successful")
        return {"message": "Password updated successfully"}
    except (TokenError, NotFoundError) as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise

@router.post("/request-otp", response_model=Message)
def request_otp(
    email_address: str,
    background_tasks: BackgroundTasks,
    purpose: str = "password_reset",
    db: Session = Depends(get_db)
):
    """
    Request OTP for various purposes (password_reset, phone_verification, etc.)
    """
    try:
        logger.info(f"OTP request for email: {email_address}, purpose: {purpose}")
        otp = otp_service.create_otp(db, email_address, purpose)
        
        if purpose == "password_reset":
            background_tasks.add_task(
                email.send_otp_email,
                email_to=email_address,
                otp_code=otp.otp_code,
                purpose="password_reset"
            )
        
        logger.info(f"OTP sent successfully to {email_address}")
        return {"message": "OTP sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send OTP to {email_address}: {str(e)}", exc_info=True)
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

@router.post("/google", response_model=Token)
async def google_auth(
    auth_data: GoogleAuth,
    db: Session = Depends(get_db)
):
    """
    Authenticate or register user with Google
    """
    try:
        logger.info(f"Google OAuth attempt for email: {auth_data.email}")
        google_data = await social_auth.verify_google_token(auth_data.token)
        user = await social_auth.get_or_create_google_user(db, google_data)
        result = social_auth.create_social_auth_token(user)
        logger.info(f"Google OAuth successful for user: {user.email}")
        return result
    except Exception as e:
        logger.error(f"Google OAuth failed for {auth_data.email}: {str(e)}", exc_info=True)
        raise OAuthError("Google OAuth authentication failed", details={"original_error": str(e)})

@router.post("/facebook", response_model=Token)
async def facebook_auth(
    auth_data: FacebookAuth,
    db: Session = Depends(get_db)
):
    """
    Authenticate or register user with Facebook
    """
    try:
        logger.info(f"Facebook OAuth attempt for email: {auth_data.email}")
        facebook_data = await social_auth.verify_facebook_token(auth_data.token)
        user = await social_auth.get_or_create_facebook_user(db, facebook_data)
        result = social_auth.create_social_auth_token(user)
        logger.info(f"Facebook OAuth successful for user: {user.email}")
        return result
    except Exception as e:
        logger.error(f"Facebook OAuth failed for {auth_data.email}: {str(e)}", exc_info=True)
        raise OAuthError("Facebook OAuth authentication failed", details={"original_error": str(e)})

@router.post("/data-deletion", response_model=Message)
async def data_deletion(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint for Facebook data deletion requests.
    This endpoint will be called by Facebook when a user requests data deletion.
    """
    try:
        logger.info("Facebook data deletion request received")
        # Get the signed request from Facebook
        signed_request = await request.json()
        
        # Verify the request is from Facebook
        if not signed_request.get('user_id'):
            logger.warning("Invalid data deletion request: No user_id")
            raise ValidationError("Invalid request")
        
        # Find and delete the user's data
        user = db.query(User).filter(User.facebook_id == signed_request['user_id']).first()
        if user:
            # Delete user data
            db.delete(user)
            db.commit()
            logger.info(f"User data deleted successfully for Facebook ID: {signed_request['user_id']}")
            
            return {
                "message": "User data deleted successfully",
                "url": f"{settings.FRONTEND_URL}/data-deletion-confirmation",
                "confirmation_code": signed_request['user_id']
            }
        
        logger.info(f"No user data found for Facebook ID: {signed_request['user_id']}")
        return {
            "message": "No user data found",
            "url": f"{settings.FRONTEND_URL}/data-deletion-confirmation",
            "confirmation_code": signed_request['user_id']
        }
        
    except Exception as e:
        logger.error(f"Data deletion request failed: {str(e)}", exc_info=True)
        raise DatabaseError("Error processing data deletion request", details={"original_error": str(e)})

@router.get("/data-deletion-status/{user_id}", response_model=Message)
async def data_deletion_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check data deletion status for a user
    """
    try:
        logger.info(f"Data deletion status check for user ID: {user_id}")
        user = db.query(User).filter(User.facebook_id == user_id).first()
        
        if user:
            return {"message": "User data still exists"}
        else:
            return {"message": "User data has been deleted"}
    except Exception as e:
        logger.error(f"Data deletion status check failed for {user_id}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to check data deletion status", details={"original_error": str(e)})