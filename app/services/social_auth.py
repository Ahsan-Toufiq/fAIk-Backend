from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from google.oauth2 import id_token
from google.auth.transport import requests
from facebook import GraphAPI
from sqlalchemy.orm import Session

from app.models.users import User
from app.config import settings
from app.utils.security import create_access_token
from datetime import timedelta

async def verify_google_token(token: str) -> Dict[str, Any]:
    try:
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer')
            
        return idinfo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

async def verify_facebook_token(token: str) -> Dict[str, Any]:
    try:
        graph = GraphAPI(access_token=token)
        user_info = graph.get_object(
            id='me',
            fields='id,email,first_name,last_name'
        )
        
        # Verify the token is valid by making a test API call
        graph.get_object('me')
        
        return user_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Facebook token: {str(e)}"
        )

async def get_or_create_google_user(db: Session, google_data: Dict[str, Any]) -> User:
    user = db.query(User).filter(User.google_id == google_data['sub']).first()
    
    if not user:
        # Check if user with this email exists
        user = db.query(User).filter(User.email == google_data['email']).first()
        if user:
            # Link existing user with Google
            user.google_id = google_data['sub']
            user.is_email_verified = True
            db.commit()
        else:
            # Create new user
            user = User(
                email=google_data['email'],
                first_name=google_data.get('given_name'),
                last_name=google_data.get('family_name'),
                google_id=google_data['sub'],
                is_active=True,
                is_verified=True,
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    
    return user

async def get_or_create_facebook_user(db: Session, facebook_data: Dict[str, Any]) -> User:
    user = db.query(User).filter(User.facebook_id == facebook_data['id']).first()
    
    if not user:
        # Check if user with this email exists
        user = db.query(User).filter(User.email == facebook_data['email']).first()
        if user:
            # Link existing user with Facebook
            user.facebook_id = facebook_data['id']
            user.is_email_verified = True
            db.commit()
        else:
            # Create new user
            user = User(
                email=facebook_data['email'],
                first_name=facebook_data.get('first_name'),
                last_name=facebook_data.get('last_name'),
                facebook_id=facebook_data['id'],
                is_active=True,
                is_verified=True,
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    
    return user

def create_social_auth_token(user: User) -> Dict[str, str]:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"} 