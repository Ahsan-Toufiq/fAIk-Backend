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


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create new user with email and password
    """
    return create_user(db=db, user=user)

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/microsoft/login")
def microsoft_login():
    """
    Get Microsoft OAuth login URL
    """
    return {"url": microsoft_auth_service.get_authorization_url()}

@router.post("/microsoft/callback", response_model=Token)
async def microsoft_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle Microsoft OAuth callback
    """
    user = await microsoft_auth_service.authenticate_user(db, code)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user information
    """
    return current_user

@router.post("/verify-email", response_model=UserOut)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify user's email using the verification token
    """
    return verify_email(db=db, token=token)

@router.post("/resend-verification", response_model=Message)
def resend_verification(
    background_tasks: BackgroundTasks,
    email_address: str,
    db: Session = Depends(get_db),
):
    """
    Resend verification email
    """
    user = db.query(User).filter(User.email == email_address).first()
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
    
    return {"message": "Verification email resent successfully"}

@router.post("/forgot-password", response_model=Message)
def forgot_password(
    background_tasks: BackgroundTasks,
    email_address: str,
    db: Session = Depends(get_db),
):
    """
    Request password reset
    """
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
    
    # Always return success to prevent email enumeration
    return {"message": "If this email exists, a password reset link has been sent"}

@router.post("/reset-password", response_model=Message)
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from email
    """
    reset_password(db=db, token=token, new_password=new_password)
    return {"message": "Password updated successfully"}


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
    otp = otp_service.create_otp(db, email_address, purpose)
    
    if purpose == "password_reset":
        subject = "Your Password Reset OTP"
        html_content = f"""
        <html>
        <body>
            <p>Your OTP for password reset is: <strong>{otp.otp_code}</strong></p>
            <p>This OTP will expire in 15 minutes.</p>
        </body>
        </html>
        """
        background_tasks.add_task(
            email.send_email,
            email_to=email_address,
            subject=subject,
            html_content=html_content  # Using direct HTML content
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

@router.post("/google", response_model=Token)
async def google_auth(
    auth_data: GoogleAuth,
    db: Session = Depends(get_db)
):
    """
    Authenticate or register user with Google
    """
    try:
        google_data = await social_auth.verify_google_token(auth_data.token)
        user = await social_auth.get_or_create_google_user(db, google_data)
        return social_auth.create_social_auth_token(user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during Google authentication: {str(e)}"
        )

@router.post("/facebook", response_model=Token)
async def facebook_auth(
    auth_data: FacebookAuth,
    db: Session = Depends(get_db)
):
    """
    Authenticate or register user with Facebook
    """
    try:
        facebook_data = await social_auth.verify_facebook_token(auth_data.token)
        user = await social_auth.get_or_create_facebook_user(db, facebook_data)
        return social_auth.create_social_auth_token(user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during Facebook authentication: {str(e)}"
        )

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
        # Get the signed request from Facebook
        signed_request = await request.json()
        
        # Verify the request is from Facebook
        if not signed_request.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request"
            )
        
        # Find and delete the user's data
        user = db.query(User).filter(User.facebook_id == signed_request['user_id']).first()
        if user:
            # Delete user data
            db.delete(user)
            db.commit()
            
            return {
                "message": "User data deleted successfully",
                "url": f"{settings.FRONTEND_URL}/data-deletion-confirmation",
                "confirmation_code": signed_request['user_id']
            }
        
        return {
            "message": "No user data found",
            "url": f"{settings.FRONTEND_URL}/data-deletion-confirmation",
            "confirmation_code": signed_request['user_id']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing data deletion request: {str(e)}"
        )

@router.get("/data-deletion-status/{user_id}", response_model=Message)
async def data_deletion_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check the status of a data deletion request
    """
    user = db.query(User).filter(User.facebook_id == user_id).first()
    if not user:
        return {"message": "Data deletion completed"}
    return {"message": "Data deletion in progress"}