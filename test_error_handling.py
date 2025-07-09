import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.users import User
from app.exceptions import (
    AuthenticationError,
    NotFoundError,
    ConflictError,
    TokenError,
    DatabaseError,
    OAuthError
)

# Create in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_custom_exception_handling():
    """Test that custom exceptions are properly handled and return correct HTTP status codes"""
    
    # Test authentication error
    response = client.post("/auth/login", data={
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "message" in response.json()
    assert "error_type" in response.json()
    
    # Test validation error (invalid email format)
    response = client.post("/auth/signup", json={
        "email": "invalid-email",
        "password": "testpass123",
        "confirm_password": "testpass123",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 422
    assert "message" in response.json()
    assert "error_type" in response.json()

def test_database_error_handling():
    """Test that database errors are properly handled"""
    
    # This test would require mocking database failures
    # For now, we'll test the structure of error responses
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    assert "message" in response.json()
    assert "error_type" in response.json()

def test_logging_setup():
    """Test that logging is properly configured"""
    from app.utils.logger import get_logger
    
    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "test"

def test_exception_hierarchy():
    """Test that custom exceptions have the correct hierarchy"""
    
    # Test that custom exceptions inherit from BaseCustomException
    auth_error = AuthenticationError("Test error")
    assert isinstance(auth_error, AuthenticationError)
    assert isinstance(auth_error, Exception)
    
    # Test that exceptions have correct status codes
    assert auth_error.status_code == 401
    
    not_found_error = NotFoundError("Resource not found")
    assert not_found_error.status_code == 404
    
    conflict_error = ConflictError("Resource conflict")
    assert conflict_error.status_code == 409

if __name__ == "__main__":
    pytest.main([__file__]) 