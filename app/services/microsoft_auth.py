from typing import Optional, Dict
import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.users import User
from app.config import settings
from app.utils import security

class MicrosoftAuthService:
    def __init__(self):
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = settings.MICROSOFT_TENANT_ID
        self.redirect_uri = f"{settings.FRONTEND_URL}/auth/microsoft/callback"
        self.scope = "openid profile email"
        self.authorize_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.userinfo_url = "https://graph.microsoft.com/v1.0/me"

    def get_authorization_url(self) -> str:
        """Generate Microsoft OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_mode": "query"
        }
        return f"{self.authorize_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    async def get_access_token(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(self.token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Microsoft"
            )
        return response.json()

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Microsoft Graph API"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.userinfo_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Microsoft"
            )
        return response.json()

    async def authenticate_user(self, db: Session, code: str) -> User:
        """Authenticate user with Microsoft OAuth"""
        # Get access token
        token_data = await self.get_access_token(code)
        access_token = token_data["access_token"]
        
        # Get user info
        user_info = await self.get_user_info(access_token)
        
        # Check if user exists
        user = db.query(User).filter(User.microsoft_id == user_info["id"]).first()
        if user:
            return user
        
        # Check if email exists
        user = db.query(User).filter(User.email == user_info["mail"]).first()
        if user:
            # Update existing user with Microsoft ID
            user.microsoft_id = user_info["id"]
            db.commit()
            return user
        
        # Create new user
        new_user = User(
            email=user_info["mail"],
            first_name=user_info.get("givenName"),
            last_name=user_info.get("surname"),
            microsoft_id=user_info["id"],
            is_active=True,
            is_verified=True,
            is_email_verified=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user

microsoft_auth_service = MicrosoftAuthService() 