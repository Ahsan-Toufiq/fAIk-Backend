import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    # Test data
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    # 1. Test Signup
    print("\n1. Testing Signup...")
    signup_response = requests.post(
        f"{BASE_URL}/auth/signup",
        json=test_user
    )
    print(f"Signup Response: {signup_response.status_code}")
    print(json.dumps(signup_response.json(), indent=2))
    
    # 2. Test Login
    print("\n2. Testing Login...")
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"]
    }
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data=login_data
    )
    print(f"Login Response: {login_response.status_code}")
    print(json.dumps(login_response.json(), indent=2))
    
    if login_response.status_code == 200:
        access_token = login_response.json()["access_token"]
        
        # 3. Test Protected Endpoint (GET /me)
        print("\n3. Testing Protected Endpoint...")
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=headers
        )
        print(f"Protected Endpoint Response: {me_response.status_code}")
        print(json.dumps(me_response.json(), indent=2))

if __name__ == "__main__":
    test_auth_flow() 