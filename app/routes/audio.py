from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
import logging
from app.services.model_service import model_service
import torch
import numpy as np
import io
import librosa
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

class ChunkAnalysis(BaseModel):
    chunk_index: int
    start_time: float
    end_time: float
    is_ai_generated: bool
    confidence: float
    class_probabilities: dict

class AudioAnalysisResponse(BaseModel):
    is_deepfake: bool
    overall_confidence: float
    model_loaded: bool
    total_chunks: int
    chunks: List[ChunkAnalysis]
    summary: dict

@router.get("/model-status")
async def get_model_status():
    """Check if the audio classification model is loaded"""
    return {
        "model_loaded": model_service.is_model_loaded(),
        "model_name": model_service.model_name if model_service.is_model_loaded() else None
    }

@router.post("/analyze-audio", response_model=AudioAnalysisResponse)
async def analyze_audio(
    audio_file: UploadFile = File(...),
    chunk_duration: float = Query(5.0, description="Duration of each chunk in seconds", ge=1.0, le=30.0),
    overlap: float = Query(0.5, description="Overlap between chunks (0.0 to 1.0)", ge=0.0, le=0.9)
):
    """
    Analyze an audio file for deepfake detection by processing it in chunks
    """
    if not model_service.is_model_loaded():
        raise HTTPException(
            status_code=503, 
            detail="Audio classification model is not loaded. Please try again later."
        )
    
    try:
        # Read the audio file
        audio_data = await audio_file.read()
        
        # Load audio using librosa
        audio_bytes = io.BytesIO(audio_data)
        audio, sample_rate = librosa.load(audio_bytes, sr=16000)  # Resample to 16kHz
        
        # Get model and feature extractor
        model = model_service.get_model()
        feature_extractor = model_service.get_feature_extractor()
        
        # Calculate chunk parameters
        chunk_samples = int(chunk_duration * sample_rate)
        overlap_samples = int(overlap * chunk_samples)
        step_samples = chunk_samples - overlap_samples
        
        # Ensure we have at least one chunk
        if len(audio) < chunk_samples:
            # If audio is shorter than chunk duration, pad it
            audio = np.pad(audio, (0, chunk_samples - len(audio)))
            logger.info(f"Audio file shorter than chunk duration. Padded to {len(audio)} samples")
        
        # Process audio in chunks
        chunks = []
        total_chunks = 0
        ai_generated_chunks = 0
        
        # Calculate the number of chunks we can create
        num_chunks = max(1, (len(audio) - chunk_samples) // step_samples + 1)
        logger.info(f"Audio length: {len(audio)} samples ({len(audio)/sample_rate:.2f}s)")
        logger.info(f"Chunk samples: {chunk_samples} ({chunk_duration}s)")
        logger.info(f"Step samples: {step_samples}")
        logger.info(f"Expected chunks: {num_chunks}")
        
        for i in range(0, len(audio) - chunk_samples + 1, step_samples):
            chunk_audio = audio[i:i + chunk_samples]
            
            # Ensure chunk has the right size
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
                
                # Create chunk analysis
                chunk_analysis = ChunkAnalysis(
                    chunk_index=total_chunks,
                    start_time=i / sample_rate,
                    end_time=(i + chunk_samples) / sample_rate,
                    is_ai_generated=is_ai_generated,
                    confidence=confidence,
                    class_probabilities={
                        "ai_generated": probabilities[0][0].item(),
                        "real": probabilities[0][1].item()
                    }
                )
                chunks.append(chunk_analysis)
                total_chunks += 1
                
                logger.info(f"Processed chunk {total_chunks}: {i/sample_rate:.1f}s-{(i+chunk_samples)/sample_rate:.1f}s, "
                           f"Prediction: {'AI Generated' if is_ai_generated else 'Real'}, "
                           f"Confidence: {confidence:.3f}")
        
        # If no chunks were created, create at least one chunk from the entire audio
        if total_chunks == 0:
            logger.warning("No chunks created, processing entire audio as single chunk")
            chunk_audio = audio
            if len(chunk_audio) < chunk_samples:
                chunk_audio = np.pad(chunk_audio, (0, chunk_samples - len(chunk_audio)))
            
            inputs = feature_extractor(
                chunk_audio, 
                sampling_rate=sample_rate, 
                return_tensors="pt"
            )
            
            with torch.no_grad():
                outputs = model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(probabilities, dim=-1).item()
                confidence = torch.max(probabilities, dim=-1)[0].item()
                is_ai_generated = predicted_class == 0
                
                if is_ai_generated:
                    ai_generated_chunks += 1
                
                chunk_analysis = ChunkAnalysis(
                    chunk_index=0,
                    start_time=0.0,
                    end_time=len(audio) / sample_rate,
                    is_ai_generated=is_ai_generated,
                    confidence=confidence,
                    class_probabilities={
                        "ai_generated": probabilities[0][0].item(),
                        "real": probabilities[0][1].item()
                    }
                )
                chunks.append(chunk_analysis)
                total_chunks = 1
        
        # Calculate overall results
        if total_chunks > 0:
            ai_generated_ratio = ai_generated_chunks / total_chunks
            is_deepfake = ai_generated_ratio > 0.5  # More than 50% chunks are AI generated
            overall_confidence = sum(chunk.confidence for chunk in chunks) / total_chunks
        else:
            is_deepfake = False
            overall_confidence = 0.0
        
        # Create summary
        summary = {
            "total_chunks": total_chunks,
            "ai_generated_chunks": ai_generated_chunks,
            "real_chunks": total_chunks - ai_generated_chunks,
            "ai_generated_ratio": ai_generated_ratio if total_chunks > 0 else 0.0,
            "average_confidence": overall_confidence,
            "chunk_duration_seconds": chunk_duration,
            "overlap_ratio": overlap
        }
        
        logger.info(f"Audio analysis completed for file: {audio_file.filename}. "
                   f"Processed {total_chunks} chunks, {ai_generated_chunks} AI-generated")
        
        return AudioAnalysisResponse(
            is_deepfake=is_deepfake,
            overall_confidence=overall_confidence,
            model_loaded=True,
            total_chunks=total_chunks,
            chunks=chunks,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error analyzing audio file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing audio file: {str(e)}"
        )

@router.post("/debug-audio")
async def debug_audio(audio_file: UploadFile = File(...)):
    """
    Debug endpoint to check audio file properties
    """
    try:
        # Read the audio file
        audio_data = await audio_file.read()
        
        # Load audio using librosa
        audio_bytes = io.BytesIO(audio_data)
        audio, sample_rate = librosa.load(audio_bytes, sr=16000)  # Resample to 16kHz
        
        # Calculate various chunk parameters
        chunk_durations = [1.0, 3.0, 5.0, 10.0]
        overlap_ratios = [0.0, 0.3, 0.5, 0.7]
        
        chunk_info = {}
        for chunk_duration in chunk_durations:
            for overlap in overlap_ratios:
                chunk_samples = int(chunk_duration * sample_rate)
                overlap_samples = int(overlap * chunk_samples)
                step_samples = chunk_samples - overlap_samples
                
                if step_samples > 0:
                    num_chunks = max(1, (len(audio) - chunk_samples) // step_samples + 1)
                else:
                    num_chunks = 1
                
                key = f"{chunk_duration}s_{int(overlap*100)}%"
                chunk_info[key] = {
                    "chunk_duration": chunk_duration,
                    "overlap": overlap,
                    "chunk_samples": chunk_samples,
                    "step_samples": step_samples,
                    "num_chunks": num_chunks,
                    "audio_duration": len(audio) / sample_rate,
                    "audio_samples": len(audio)
                }
        
        return {
            "filename": audio_file.filename,
            "file_size_bytes": len(audio_data),
            "audio_duration_seconds": len(audio) / sample_rate,
            "audio_samples": len(audio),
            "sample_rate": sample_rate,
            "chunk_analysis": chunk_info
        }
        
    except Exception as e:
        logger.error(f"Error debugging audio file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error debugging audio file: {str(e)}"
        )

@router.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    if not model_service.is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="Model is not loaded"
        )
    
    model = model_service.get_model()
    feature_extractor = model_service.get_feature_extractor()
    
    return {
        "model_name": model_service.model_name,
        "model_type": type(model).__name__,
        "feature_extractor_type": type(feature_extractor).__name__,
        "model_config": str(model.config) if hasattr(model, 'config') else "No config available",
        "num_classes": model.config.num_labels if hasattr(model.config, 'num_labels') else "Unknown",
        "class_mapping": {
            "0": "AI Generated",
            "1": "Real"
        }
    } 