from pydantic import PostgresDsn
from pydantic import BaseSettings
from typing import Optional
from pydantic import validator

class Settings(BaseSettings):
    # PostgreSQL Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: Optional[str] = None  # For Azure AD
    
    # Email configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM: Optional[str] = None
    SMTP_TLS: bool = True  # Default to True for security
    SMTP_SSL: bool = False  # Typically use either TLS or SSL, not both

    FRONTEND_URL: str = "http://localhost:3000"
    
    @validator("SMTP_PORT", pre=True, always=True)
    def cast_smtp_port(cls, v):
        if v is None:
            return 587
        # Remove comments and whitespace
        if isinstance(v, str):
            v = v.split('#')[0].strip()
        return int(v)

    class Config:
        env_file = ".env"

settings = Settings()