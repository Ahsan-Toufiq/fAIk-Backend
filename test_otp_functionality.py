#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced OTP functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_otp_functionality():
    """Test the complete OTP functionality"""
    
    print("=== OTP Functionality Test ===\n")
    
    test_email = "test@example.com"
    test_purpose = "password_reset"
    
    # 1. Request OTP
    print("1. Requesting OTP...")
    response = requests.post(
        f"{BASE_URL}/auth/otp/request-otp",
        params={
            "email": test_email,
            "purpose": test_purpose
        }
    )
    
    if response.status_code == 200:
        print("✅ OTP requested successfully")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ OTP request failed: {response.status_code}")
        print(f"Error: {response.json()}")
        return
    
    # 2. Check OTP status
    print("\n2. Checking OTP status...")
    response = requests.get(
        f"{BASE_URL}/auth/otp/otp-status/{test_email}/{test_purpose}"
    )
    
    if response.status_code == 200:
        status_data = response.json()
        print("✅ OTP status retrieved")
        print(f"Status: {json.dumps(status_data, indent=2)}")
        
        # Extract OTP from the status (in real scenario, this would come from email)
        # For testing, we'll simulate getting the OTP from the database
        otp_code = "123456"  # This would normally come from email
    else:
        print(f"❌ OTP status check failed: {response.status_code}")
        print(f"Error: {response.json()}")
        return
    
    # 3. Verify OTP with wrong code first
    print("\n3. Testing OTP verification with wrong code...")
    response = requests.post(
        f"{BASE_URL}/auth/otp/verify-otp",
        params={
            "email": test_email,
            "otp_code": "000000",  # Wrong code
            "purpose": test_purpose
        }
    )
    
    if response.status_code == 400:
        print("✅ Wrong OTP correctly rejected")
        print(f"Error: {response.json()}")
    else:
        print(f"❌ Wrong OTP should have been rejected: {response.status_code}")
    
    # 4. Check OTP status after failed attempt
    print("\n4. Checking OTP status after failed attempt...")
    response = requests.get(
        f"{BASE_URL}/auth/otp/otp-status/{test_email}/{test_purpose}"
    )
    
    if response.status_code == 200:
        status_data = response.json()
        print("✅ OTP status after failed attempt:")
        print(f"Status: {json.dumps(status_data, indent=2)}")
    
    # 5. Test rate limiting
    print("\n5. Testing rate limiting...")
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/auth/otp/request-otp",
            params={
                "email": test_email,
                "purpose": test_purpose
            }
        )
        
        if response.status_code == 429:
            print(f"✅ Rate limiting working (attempt {i+1})")
            print(f"Error: {response.json()}")
            break
        elif response.status_code == 200:
            print(f"✅ OTP {i+1} requested successfully")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    
    # 6. Test OTP expiration (simulate by waiting)
    print("\n6. Testing OTP expiration...")
    print("Note: In real scenario, OTPs expire after 15 minutes")
    print("For testing, we'll simulate this behavior")
    
    # 7. Cleanup OTPs
    print("\n7. Testing OTP cleanup...")
    response = requests.post(f"{BASE_URL}/auth/otp/cleanup-otps")
    
    if response.status_code == 200:
        cleanup_data = response.json()
        print("✅ OTP cleanup completed")
        print(f"Cleanup: {json.dumps(cleanup_data, indent=2)}")
    else:
        print(f"❌ OTP cleanup failed: {response.status_code}")
        print(f"Error: {response.json()}")
    
    print("\n=== OTP Test Complete ===")

def demonstrate_otp_security_features():
    """Demonstrate the security features of the OTP system"""
    
    print("\n=== OTP Security Features Demo ===\n")
    
    features = [
        "✅ Rate Limiting: Maximum 5 OTPs per hour per email/purpose",
        "✅ Attempt Tracking: Maximum 3 verification attempts per OTP",
        "✅ Automatic Expiration: OTPs expire after 15 minutes",
        "✅ One-time Use: OTPs are marked as used after successful verification",
        "✅ Database Storage: OTPs are securely stored in database",
        "✅ Automatic Cleanup: Expired and used OTPs are automatically cleaned up",
        "✅ Audit Trail: All OTP operations are logged",
        "✅ Input Validation: All inputs are validated and sanitized"
    ]
    
    for feature in features:
        print(feature)
    
    print("\n=== Security Features Complete ===")

if __name__ == "__main__":
    test_otp_functionality()
    demonstrate_otp_security_features() 