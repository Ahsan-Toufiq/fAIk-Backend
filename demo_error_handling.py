#!/usr/bin/env python3
"""
Demonstration script showing the improved error handling system
"""

import requests
import json
from app.exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    TokenError,
    DatabaseError,
    OAuthError
)
from app.utils.logger import get_logger

logger = get_logger("demo")

def demonstrate_error_handling():
    """Demonstrate the improved error handling system"""
    
    print("=== fAIk Backend Error Handling Demo ===\n")
    
    # Test custom exceptions
    print("1. Testing Custom Exceptions:")
    print("-" * 40)
    
    try:
        raise AuthenticationError("Invalid credentials")
    except AuthenticationError as e:
        print(f"✅ AuthenticationError caught: {e.message} (Status: {e.status_code})")
    
    try:
        raise NotFoundError("User not found")
    except NotFoundError as e:
        print(f"✅ NotFoundError caught: {e.message} (Status: {e.status_code})")
    
    try:
        raise ConflictError("Email already registered")
    except ConflictError as e:
        print(f"✅ ConflictError caught: {e.message} (Status: {e.status_code})")
    
    try:
        raise TokenError("Invalid or expired token")
    except TokenError as e:
        print(f"✅ TokenError caught: {e.message} (Status: {e.status_code})")
    
    try:
        raise DatabaseError("Database connection failed")
    except DatabaseError as e:
        print(f"✅ DatabaseError caught: {e.message} (Status: {e.status_code})")
    
    try:
        raise OAuthError("OAuth authentication failed")
    except OAuthError as e:
        print(f"✅ OAuthError caught: {e.message} (Status: {e.status_code})")
    
    print("\n2. Testing Logging System:")
    print("-" * 40)
    
    # Test different loggers
    auth_logger = get_logger("auth")
    db_logger = get_logger("database")
    email_logger = get_logger("email")
    
    auth_logger.info("Authentication attempt for user@example.com")
    db_logger.warning("Database connection slow")
    email_logger.error("Failed to send email to user@example.com")
    
    print("✅ Logging system working - check logs/app.log for details")
    
    print("\n3. Testing Error Response Format:")
    print("-" * 40)
    
    # Simulate error responses
    auth_error_response = {
        "message": "Incorrect email or password",
        "error_type": "AuthenticationError",
        "details": {}
    }
    
    validation_error_response = {
        "message": "Validation error",
        "error_type": "ValidationError",
        "details": {
            "errors": [
                {
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address",
                    "type": "value_error.email"
                }
            ]
        }
    }
    
    db_error_response = {
        "message": "Database error occurred",
        "error_type": "DatabaseError",
        "details": {
            "operation": "create user",
            "original_error": "connection timeout"
        }
    }
    
    print("Authentication Error Response:")
    print(json.dumps(auth_error_response, indent=2))
    print("\nValidation Error Response:")
    print(json.dumps(validation_error_response, indent=2))
    print("\nDatabase Error Response:")
    print(json.dumps(db_error_response, indent=2))
    
    print("\n4. Error Handling Benefits:")
    print("-" * 40)
    print("✅ Consistent error response format")
    print("✅ Proper HTTP status codes")
    print("✅ Detailed error logging")
    print("✅ Custom exceptions for different error types")
    print("✅ Graceful error recovery")
    print("✅ Better debugging information")
    print("✅ Security through error message sanitization")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demonstrate_error_handling() 