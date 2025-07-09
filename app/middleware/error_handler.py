from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose import JWTError
import traceback
from typing import Union

from app.exceptions import BaseCustomException, convert_to_http_exception
from app.utils.logger import get_logger

logger = get_logger("error_handler")


async def error_handler_middleware(request: Request, call_next):
    """
    Global error handling middleware
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        JSONResponse with error details
    """
    try:
        response = await call_next(request)
        return response
    except BaseCustomException as e:
        # Handle custom exceptions
        logger.error(f"Custom exception: {e.message}", extra={"details": e.details})
        http_exception = convert_to_http_exception(e)
        return JSONResponse(
            status_code=http_exception.status_code,
            content=http_exception.detail
        )
    except RequestValidationError as e:
        # Handle validation errors
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Validation error",
                "error_type": "ValidationError",
                "details": {
                    "errors": e.errors(),
                    "body": e.body
                }
            }
        )
    except SQLAlchemyError as e:
        # Handle database errors
        logger.error(f"Database error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Database error occurred",
                "error_type": "DatabaseError",
                "details": {
                    "operation": "database_operation",
                    "original_error": str(e)
                }
            }
        )
    except JWTError as e:
        # Handle JWT errors
        logger.error(f"JWT error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "message": "Invalid token",
                "error_type": "TokenError",
                "details": {
                    "original_error": str(e)
                }
            }
        )
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error",
                "error_type": "InternalServerError",
                "details": {
                    "original_error": str(e),
                    "traceback": traceback.format_exc() if logger.isEnabledFor(logger.DEBUG) else None
                }
            }
        )


def setup_error_handlers(app):
    """
    Set up error handlers for the FastAPI app
    
    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import SQLAlchemyError
    from jose import JWTError
    
    @app.exception_handler(BaseCustomException)
    async def custom_exception_handler(request: Request, exc: BaseCustomException):
        """Handle custom exceptions"""
        logger.error(f"Custom exception: {exc.message}", extra={"details": exc.details})
        http_exception = convert_to_http_exception(exc)
        return JSONResponse(
            status_code=http_exception.status_code,
            content=http_exception.detail
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.error(f"Validation error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Validation error",
                "error_type": "ValidationError",
                "details": {
                    "errors": exc.errors(),
                    "body": exc.body
                }
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors"""
        logger.error(f"Database error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Database error occurred",
                "error_type": "DatabaseError",
                "details": {
                    "operation": "database_operation",
                    "original_error": str(exc)
                }
            }
        )
    
    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError):
        """Handle JWT errors"""
        logger.error(f"JWT error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "message": "Invalid token",
                "error_type": "TokenError",
                "details": {
                    "original_error": str(exc)
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle any other unexpected errors"""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error",
                "error_type": "InternalServerError",
                "details": {
                    "original_error": str(exc),
                    "traceback": traceback.format_exc() if logger.isEnabledFor(logger.DEBUG) else None
                }
            }
        ) 