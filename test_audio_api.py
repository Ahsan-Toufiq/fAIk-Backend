#!/usr/bin/env python3
"""
Test script to verify the audio API endpoint
"""

import requests
import numpy as np
import io
import wave
import tempfile
import os

def create_test_wav_file(duration_seconds=10, sample_rate=16000):
    """Create a test WAV file for testing"""
    # Generate a simple sine wave
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Normalize audio
    audio = audio / np.max(np.abs(audio))
    
    # Convert to 16-bit PCM
    audio = (audio * 32767).astype(np.int16)
    
    # Create WAV file in memory
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())
        
        return temp_file.name

def test_audio_api():
    """Test the audio analysis API endpoint"""
    print("Testing audio analysis API...")
    
    try:
        # Create test audio file
        test_file_path = create_test_wav_file(duration_seconds=15)
        print(f"✅ Created test audio file: {test_file_path}")
        
        # Test model status endpoint
        print("\n1. Testing model status endpoint...")
        response = requests.get("http://localhost:8000/audio/model-status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ Model status: {status_data}")
        else:
            print(f"❌ Model status failed: {response.status_code}")
            return False
        
        # Test model info endpoint
        print("\n2. Testing model info endpoint...")
        response = requests.get("http://localhost:8000/audio/model-info")
        if response.status_code == 200:
            info_data = response.json()
            print(f"✅ Model info: {info_data}")
        else:
            print(f"❌ Model info failed: {response.status_code}")
            return False
        
        # Test audio analysis endpoint
        print("\n3. Testing audio analysis endpoint...")
        with open(test_file_path, 'rb') as audio_file:
            files = {'audio_file': ('test_audio.wav', audio_file, 'audio/wav')}
            params = {
                'chunk_duration': 3.0,
                'overlap': 0.3
            }
            
            response = requests.post(
                "http://localhost:8000/audio/analyze-audio",
                files=files,
                params=params
            )
        
        if response.status_code == 200:
            analysis_data = response.json()
            print(f"✅ Audio analysis successful!")
            print(f"   Is deepfake: {analysis_data['is_deepfake']}")
            print(f"   Overall confidence: {analysis_data['overall_confidence']:.3f}")
            print(f"   Total chunks: {analysis_data['total_chunks']}")
            print(f"   AI generated chunks: {analysis_data['summary']['ai_generated_chunks']}")
            print(f"   Real chunks: {analysis_data['summary']['real_chunks']}")
            print(f"   AI generated ratio: {analysis_data['summary']['ai_generated_ratio']:.3f}")
            
            # Show first few chunks
            print(f"\n   First 3 chunks:")
            for i, chunk in enumerate(analysis_data['chunks'][:3]):
                print(f"     Chunk {i}: {chunk['start_time']:.1f}s-{chunk['end_time']:.1f}s")
                print(f"       {'AI Generated' if chunk['is_ai_generated'] else 'Real'}")
                print(f"       Confidence: {chunk['confidence']:.3f}")
        else:
            print(f"❌ Audio analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Clean up
        os.unlink(test_file_path)
        print(f"\n✅ Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing audio API: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎵 Audio API Test")
    print("=" * 50)
    
    success = test_audio_api()
    if success:
        print("\n🎉 Audio API test passed!")
    else:
        print("\n💥 Audio API test failed!")
        exit(1) 