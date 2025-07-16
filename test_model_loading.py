#!/usr/bin/env python3
"""
Test script to verify model loading functionality
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.model_service import model_service

def test_model_loading():
    """Test the model loading functionality"""
    print("Testing model loading...")
    
    try:
        # Test model loading
        model_service.load_model()
        print("✅ Model loaded successfully!")
        
        # Test model access
        model = model_service.get_model()
        feature_extractor = model_service.get_feature_extractor()
        print("✅ Model and feature extractor accessible!")
        
        # Test model status
        is_loaded = model_service.is_model_loaded()
        print(f"✅ Model loaded status: {is_loaded}")
        
        print(f"Model name: {model_service.model_name}")
        print(f"Model type: {type(model).__name__}")
        print(f"Feature extractor type: {type(feature_extractor).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading model: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_model_loading()
    if success:
        print("\n🎉 Model loading test passed!")
    else:
        print("\n💥 Model loading test failed!")
        sys.exit(1) 