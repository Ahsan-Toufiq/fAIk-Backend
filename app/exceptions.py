from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class BaseCustomException(Exception):
    """Base custom exception class"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class AuthorizationError(BaseCustomException):
    """Raised when user is not authorized to perform an action"""
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class ValidationError(BaseCustomException):
    """Raised when data validation fails"""
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class NotFoundError(BaseCustomException):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class ConflictError(BaseCustomException):
    """Raised when there's a conflict (e.g., duplicate resource)"""
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_409_CONFLICT, details)


class DatabaseError(BaseCustomException):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class EmailError(BaseCustomException):
    """Raised when email operations fail"""
    def __init__(self, message: str = "Email error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class OAuthError(BaseCustomException):
    """Raised when OAuth operations fail"""
    def __init__(self, message: str = "OAuth error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class TokenError(BaseCustomException):
    """Raised when token operations fail"""
    def __init__(self, message: str = "Token error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class RateLimitError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, details)


def convert_to_http_exception(exc: BaseCustomException) -> HTTPException:
    """Convert custom exception to HTTPException"""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "error_type": exc.__class__.__name__,
            "details": exc.details
        }
    )


def handle_database_error(error: Exception, operation: str = "database operation") -> DatabaseError:
    """Handle database errors and return appropriate custom exception"""
    error_message = f"Database error during {operation}"
    
    # Log the original error for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Database error: {str(error)}", exc_info=True)
    
    return DatabaseError(
        message=error_message,
        details={"operation": operation, "original_error": str(error)}
    )


def handle_email_error(error: Exception, operation: str = "email operation") -> EmailError:
    """Handle email errors and return appropriate custom exception"""
    error_message = f"Email error during {operation}"
    
    # Log the original error for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Email error: {str(error)}", exc_info=True)
    
    return EmailError(
        message=error_message,
        details={"operation": operation, "original_error": str(error)}
    ) 