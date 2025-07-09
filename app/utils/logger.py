import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logger(
    name: str = "fAIk_backend",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional file path for logging
        log_format: Log message format
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (optional)
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger("fAIk_backend")


# Create default logger
default_logger = setup_logger()


def log_function_call(logger: logging.Logger = None):
    """
    Decorator to log function calls with parameters and return values
    
    Args:
        logger: Logger instance to use
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = logger or get_logger()
            
            # Log function call
            log.info(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                log.info(f"Function {func.__name__} completed successfully")
                return result
            except Exception as e:
                log.error(f"Function {func.__name__} failed with error: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_database_operation(operation: str):
    """
    Decorator to log database operations
    
    Args:
        operation: Description of the database operation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = get_logger("database")
            log.info(f"Starting database operation: {operation}")
            
            try:
                result = func(*args, **kwargs)
                log.info(f"Database operation '{operation}' completed successfully")
                return result
            except Exception as e:
                log.error(f"Database operation '{operation}' failed: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_email_operation(operation: str):
    """
    Decorator to log email operations
    
    Args:
        operation: Description of the email operation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = get_logger("email")
            log.info(f"Starting email operation: {operation}")
            
            try:
                result = func(*args, **kwargs)
                log.info(f"Email operation '{operation}' completed successfully")
                return result
            except Exception as e:
                log.error(f"Email operation '{operation}' failed: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_oauth_operation(provider: str):
    """
    Decorator to log OAuth operations
    
    Args:
        provider: OAuth provider name (Google, Facebook, Microsoft)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            log = get_logger("oauth")
            log.info(f"Starting {provider} OAuth operation: {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                log.info(f"{provider} OAuth operation '{func.__name__}' completed successfully")
                return result
            except Exception as e:
                log.error(f"{provider} OAuth operation '{func.__name__}' failed: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator 