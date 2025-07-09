from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.utils.logger import get_logger
from app.exceptions import DatabaseError, handle_database_error

logger = get_logger("database")

# PostgreSQL connection
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,  # Checks connection health before using
        pool_size=20,        # Number of connections to keep open
        max_overflow=30      # Number of connections beyond pool_size allowed
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}", exc_info=True)
    raise DatabaseError("Failed to initialize database connection", details={"original_error": str(e)})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Database dependency that provides a database session
    
    Yields:
        Session: Database session
        
    Raises:
        DatabaseError: If database connection fails
    """
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise handle_database_error(e, "database session")
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}", exc_info=True)
        raise DatabaseError("Database operation failed", details={"original_error": str(e)})
    finally:
        try:
            db.close()
            logger.debug("Database session closed")
        except Exception as e:
            logger.error(f"Error closing database session: {str(e)}")


def test_database_connection():
    """
    Test database connection
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}", exc_info=True)
        return False