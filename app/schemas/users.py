from pydantic import BaseModel, EmailStr, validator, constr
from typing import Optional
import re

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    @validator('first_name')
    def validate_first_name(cls, v):
        if not v:
            raise ValueError("First name is required")
        if len(v) < 2:
            raise ValueError("First name must be at least 2 characters")
        if len(v) > 50:
            raise ValueError("First name must be less than 50 characters")
        if not re.match(r"^[a-zA-Z\s\-']+$", v):
            raise ValueError("First name can only contain letters, spaces, hyphens, and apostrophes")
        return v

    @validator('last_name')
    def validate_last_name(cls, v):
        if not v:
            raise ValueError("Last name is required")
        if len(v) < 2:
            raise ValueError("Last name must be at least 2 characters")
        if len(v) > 50:
            raise ValueError("Last name must be less than 50 characters")
        if not re.match(r"^[a-zA-Z\s\-']+$", v):
            raise ValueError("Last name can only contain letters, spaces, hyphens, and apostrophes")
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if not v:
            raise ValueError("Phone number is required")
        
        # Remove any spaces, dashes, or parentheses
        cleaned_number = re.sub(r'[\s\-\(\)]', '', v)
        
        # Check if it starts with + (international format)
        if cleaned_number.startswith('+'):
            # Remove the + for length check
            number_without_plus = cleaned_number[1:]
            if not number_without_plus.isdigit():
                raise ValueError("Phone number can only contain digits after the + symbol")
            if len(number_without_plus) < 10 or len(number_without_plus) > 15:
                raise ValueError("Phone number must be between 10 and 15 digits (including country code)")
        else:
            # For numbers without +, ensure they're all digits
            if not cleaned_number.isdigit():
                raise ValueError("Phone number can only contain digits")
            if len(cleaned_number) < 10 or len(cleaned_number) > 15:
                raise ValueError("Phone number must be between 10 and 15 digits")
        
        # Store the cleaned number
        return cleaned_number

class UserCreate(UserBase):
    password: constr(min_length=8)
    confirm_password: str

    @validator('password')
    def validate_password(cls, v):
        if not v:
            raise ValueError("Password is required")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError("Passwords do not match")
        return v

class UserCreateGoogle(UserBase):
    google_id: str
    token: str  # Google auth token for verification

class UserOut(UserBase):
    id: int
    is_active: bool
    is_verified: bool

    class Config:
        orm_mode = True

class UserInDB(UserOut):
    hashed_password: str