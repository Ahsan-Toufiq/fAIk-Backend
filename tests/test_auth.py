import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, Base, engine
from app.models.users import User
from app.utils.security import get_password_hash
import time

# Create test database
Base.metadata.create_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(db: Session):
    user = User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        is_email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_signup(client: TestClient, db: Session):
    # Test valid signup
    response = client.post(
        "/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567890"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data

    # Test duplicate email
    response = client.post(
        "/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567890"
        }
    )
    assert response.status_code == 400

    # Test invalid email format
    response = client.post(
        "/auth/signup",
        json={
            "email": "invalid-email",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567890"
        }
    )
    assert response.status_code == 422

    # Test password validation
    response = client.post(
        "/auth/signup",
        json={
            "email": "user2@example.com",
            "password": "short",
            "first_name": "New",
            "last_name": "User",
            "phone": "+1234567890"
        }
    )
    assert response.status_code == 422

def test_login(client: TestClient, test_user: User):
    # Test valid login
    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid password
    response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

    # Test non-existent user
    response = client.post(
        "/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 401

def test_refresh_token(client: TestClient, test_user: User):
    # First login to get tokens
    login_response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    tokens = login_response.json()

    # Test valid refresh
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid refresh token
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401

def test_rate_limiting(client: TestClient):
    # Test login rate limiting
    for _ in range(6):  # Try 6 times (limit is 5/minute)
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
    
    assert response.status_code == 429  # Too Many Requests

    # Wait for rate limit to reset
    time.sleep(60)

def test_protected_route(client: TestClient, test_user: User):
    # First login to get token
    login_response = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    tokens = login_response.json()

    # Test protected route with valid token
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email

    # Test protected route with invalid token
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_password_reset_flow(client: TestClient, test_user: User):
    # Request password reset
    response = client.post(
        "/auth/forgot-password",
        json={"email_address": test_user.email}
    )
    assert response.status_code == 200

    # Get reset token from database
    db = next(get_db())
    user = db.query(User).filter(User.email == test_user.email).first()
    reset_token = user.reset_password_token

    # Reset password
    response = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "newpassword123"
        }
    )
    assert response.status_code == 200

    # Try login with new password
    response = client.post(
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "newpassword123"
        }
    )
    assert response.status_code == 200

def test_otp_flow(client: TestClient, test_user: User):
    # Request OTP
    response = client.post(
        "/auth/request-otp",
        json={
            "email_address": test_user.email,
            "purpose": "password_reset"
        }
    )
    assert response.status_code == 200

    # Get OTP from database
    db = next(get_db())
    otp = db.query(OTP).filter(
        OTP.email == test_user.email,
        OTP.purpose == "password_reset"
    ).first()

    # Verify OTP
    response = client.post(
        "/auth/verify-otp",
        json={
            "email": test_user.email,
            "otp_code": otp.otp_code,
            "purpose": "password_reset"
        }
    )
    assert response.status_code == 200

    # Test invalid OTP
    response = client.post(
        "/auth/verify-otp",
        json={
            "email": test_user.email,
            "otp_code": "000000",
            "purpose": "password_reset"
        }
    )
    assert response.status_code == 400 