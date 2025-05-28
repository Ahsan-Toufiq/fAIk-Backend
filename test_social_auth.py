import requests
import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from facebook import GraphAPI
from datetime import datetime, timedelta
from app.config import settings
from app.database import SessionLocal
from app.models.users import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_URL = "http://localhost:8000"

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Insert your real tokens here for demonstration
google_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImJhYTY0ZWZjMTNlZjIzNmJlOTIxZjkyMmUzYTY3Y2M5OTQxNWRiOWIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTYwMjU0ODQxMDEtMnJxMTM4bGowMHJnZTl2ZTBlYWh2dmdpZXI0ZmNtcjkuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTYwMjU0ODQxMDEtMnJxMTM4bGowMHJnZTl2ZTBlYWh2dmdpZXI0ZmNtcjkuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDM1ODc2Mzc2MTg2NzQxNTAyOTgiLCJlbWFpbCI6ImFoc2FubW9oYW1tYWR4QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdF9oYXNoIjoiMGtLZG5wTmNqY0lkcVd0Q0txQ1RGQSIsIm5hbWUiOiJNdWhhbW1hZCBBaHNhbiIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKeGZmYzdsUVFzeWtDa3FGeXRCX2hpRnVoNEVXUGZodnlKMDZKTkFWaXdjWEZYZzJRaD1zOTYtYyIsImdpdmVuX25hbWUiOiJNdWhhbW1hZCIsImZhbWlseV9uYW1lIjoiQWhzYW4iLCJpYXQiOjE3NDg0MzI1NzYsImV4cCI6MTc0ODQzNjE3Nn0.DLn8kb-HREw3SUB3r8sE_adv9xpKvxEtqfCuh2-o05f4F2ExJTvWr1ogxBzgjBXaEc-J9pA4ZmfWCEifHV03djJ3E4HD1MhywDvbDZkqEK5-lLv59X_opAivRJqPT3LyH7TkCabudiGoTE1GeUjkcN8UpetV2aEoL2MC0rNI6hF2WRKU0RYeHw91tQAfg6mzQvdrPtiHr1GOokDQrzMjir6Ys30T9QYG-PkzX1xxAGAnChQYNvMyFxl8xHlDAM8IfVddv7_MaGX83PFL8lHi6Zz5qJmbeS_XOFPcHIp1rMQMCRA2GjtyNs8HJYeChw4w-gpMHnSXcN2O6RSny_B4hQ"
facebook_token = "EAAJpLZBSGk7MBOZC1OEDLvKcO4c1cBkVCL3oLYqXG7pJ4TI7JgZBJlg0vztxmnkriIFmgbZCzVhDfdGtDtZCIKc9JZCyq8zVXkaM9ZCDdxk1Coh4WluHE4w2LVSWZCbXbi2ttKaW4tFQ3tXXVNurZBpLXbilmxMAoghnCuZBssiaVKZCEEgGwZAqxDt6htbJsqFvSBd1438v8kez62iKaEYzjZBhP2LZBopUQ3IfDeDNbKhXPKe9cQKnXMHbWqtokZCaYyp4rqQOGK2o3qXpWk70GwZD"

def setup_test_user():
    """Create a test user in the database"""
    db = SessionLocal()
    try:
        # Check if test user exists
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                is_active=True,
                is_verified=True,
                is_email_verified=True,
                google_id="test_google_id",
                facebook_id="test_facebook_id"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        return test_user
    finally:
        db.close()

def test_google_auth():
    print("\nTesting Google Authentication...")
    
    # Setup test user
    test_user = setup_test_user()
    
    test_data = {
        "token": google_token,  # Use the real Google OAuth token
        "email": test_user.email,
        "first_name": test_user.first_name,
        "last_name": test_user.last_name,
        "google_id": test_user.google_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/google",
            json=test_data
        )
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Google authentication successful!")
            return response.json()
        else:
            print("❌ Google authentication failed")
            print("Note: This is expected in the test environment without a real Google OAuth token")
            
    except Exception as e:
        print(f"Error testing Google authentication: {str(e)}")

def test_facebook_auth():
    print("\nTesting Facebook Authentication...")
    
    # Setup test user
    test_user = setup_test_user()
    
    test_data = {
        "token": facebook_token,  # Use the real Facebook OAuth token
        "email": test_user.email,
        "first_name": test_user.first_name,
        "last_name": test_user.last_name,
        "facebook_id": test_user.facebook_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/facebook",
            json=test_data
        )
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Facebook authentication successful!")
            return response.json()
        else:
            print("❌ Facebook authentication failed")
            print("Note: This is expected in the test environment without a real Facebook OAuth token")
            
    except Exception as e:
        print(f"Error testing Facebook authentication: {str(e)}")

def test_data_deletion():
    print("\nTesting Data Deletion Endpoint...")
    
    # Setup test user
    test_user = setup_test_user()
    
    test_data = {
        "user_id": test_user.facebook_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/data-deletion",
            json=test_data
        )
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Data deletion successful!")
        else:
            print("❌ Data deletion failed")
            
    except Exception as e:
        print(f"Error testing data deletion: {str(e)}")

if __name__ == "__main__":
    print("Starting social authentication tests...")
    print("Setting up test environment...")
    
    # Run tests
    google_result = test_google_auth()
    facebook_result = test_facebook_auth()
    test_data_deletion()
    
    print("\nTest Summary:")
    print("-------------")
    print("1. Google Authentication: " + ("✅ Success" if google_result else "❌ Failed "))
    print("2. Facebook Authentication: " + ("✅ Success" if facebook_result else "❌ Failed"))
    # print("3. Data Deletion: ✅ Tested")
    
    # print("\nNote: The authentication failures are expected in the test environment")
    # print("To test with real authentication:")
    # print("1. Set up Google OAuth credentials in your .env file")
    # print("2. Set up Facebook App credentials in your .env file")
    # print("3. Get real OAuth tokens from the frontend")
    # print("4. Update the test script with real tokens") 