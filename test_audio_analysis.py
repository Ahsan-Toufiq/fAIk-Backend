#!/usr/bin/env python3
"""
Test script to demonstrate chunked audio analysis functionality
"""

import sys
import os
import numpy as np
import io
import wave

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.model_service import model_service
import torch
import librosa

def create_test_audio(duration_seconds=10, sample_rate=16000):
    """Create a test audio file for testing"""
    # Generate a simple sine wave
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Normalize audio
    audio = audio / np.max(np.abs(audio))
    
    return audio, sample_rate

def test_chunked_analysis():
    """Test the chunked audio analysis functionality"""
    print("Testing chunked audio analysis...")
    
    try:
        # Load the model
        model_service.load_model()
        print("✅ Model loaded successfully!")
        
        # Create test audio
        audio, sample_rate = create_test_audio(duration_seconds=15)
        print(f"✅ Created test audio: {len(audio)} samples at {sample_rate} Hz")
        
        # Get model and feature extractor
        model = model_service.get_model()
        feature_extractor = model_service.get_feature_extractor()
        
        # Test parameters
        chunk_duration = 5.0  # seconds
        overlap = 0.5  # 50% overlap
        
        # Calculate chunk parameters
        chunk_samples = int(chunk_duration * sample_rate)
        overlap_samples = int(overlap * chunk_samples)
        step_samples = chunk_samples - overlap_samples
        
        print(f"Chunk duration: {chunk_duration}s")
        print(f"Overlap: {overlap * 100}%")
        print(f"Chunk samples: {chunk_samples}")
        print(f"Step samples: {step_samples}")
        
        # Process audio in chunks
        chunks = []
        total_chunks = 0
        ai_generated_chunks = 0
        
        for i in range(0, len(audio) - chunk_samples + 1, step_samples):
            chunk_audio = audio[i:i + chunk_samples]
            
            # Pad the last chunk if necessary
            if len(chunk_audio) < chunk_samples:
                chunk_audio = np.pad(chunk_audio, (0, chunk_samples - len(chunk_audio)))
            
            # Prepare input for the model
            inputs = feature_extractor(
                chunk_audio, 
                sampling_rate=sample_rate, 
                return_tensors="pt"
            )
            
            # Run inference
            with torch.no_grad():
                outputs = model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # Get predictions
                predicted_class = torch.argmax(probabilities, dim=-1).item()
                confidence = torch.max(probabilities, dim=-1)[0].item()
                
                # Class 0 = AI generated, Class 1 = Real
                is_ai_generated = predicted_class == 0
                if is_ai_generated:
                    ai_generated_chunks += 1
                
                print(f"Chunk {total_chunks}: {i/sample_rate:.1f}s - {(i+chunk_samples)/sample_rate:.1f}s")
                print(f"  Prediction: {'AI Generated' if is_ai_generated else 'Real'}")
                print(f"  Confidence: {confidence:.3f}")
                print(f"  Probabilities: AI={probabilities[0][0].item():.3f}, Real={probabilities[0][1].item():.3f}")
                
                chunks.append({
                    'chunk_index': total_chunks,
                    'start_time': i / sample_rate,
                    'end_time': (i + chunk_samples) / sample_rate,
                    'is_ai_generated': is_ai_generated,
                    'confidence': confidence,
                    'class_probabilities': {
                        'ai_generated': probabilities[0][0].item(),
                        'real': probabilities[0][1].item()
                    }
                })
                total_chunks += 1
        
        # Calculate overall results
        if total_chunks > 0:
            ai_generated_ratio = ai_generated_chunks / total_chunks
            is_deepfake = ai_generated_ratio > 0.5
            overall_confidence = sum(chunk['confidence'] for chunk in chunks) / total_chunks
        else:
            is_deepfake = False
            overall_confidence = 0.0
        
        print(f"\n📊 Analysis Summary:")
        print(f"Total chunks processed: {total_chunks}")
        print(f"AI generated chunks: {ai_generated_chunks}")
        print(f"Real chunks: {total_chunks - ai_generated_chunks}")
        print(f"AI generated ratio: {ai_generated_ratio:.3f}")
        print(f"Overall confidence: {overall_confidence:.3f}")
        print(f"Final classification: {'DEEPFAKE' if is_deepfake else 'REAL'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in chunked analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chunked_analysis()
    if success:
        print("\n🎉 Chunked audio analysis test passed!")
    else:
        print("\n💥 Chunked audio analysis test failed!")
        sys.exit(1) 