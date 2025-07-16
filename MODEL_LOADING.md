# Audio Classification Model Loading

This document describes how the audio classification model is integrated into the fAIk backend application.

## Overview

The application now includes automatic loading of the `mo-thecreator/Deepfake-audio-detection` model during server startup. This model is used for detecting deepfake audio files by processing them in chunks.

## Architecture

### Model Service (`app/services/model_service.py`)

The `ModelService` class handles:
- Model loading and initialization
- Feature extractor loading
- Model state management
- Error handling for model operations

### Key Features

1. **Automatic Loading**: The model is loaded during application startup
2. **Error Handling**: Graceful handling of model loading failures
3. **State Management**: Track whether the model is loaded and accessible
4. **Thread Safety**: Safe access to model instances
5. **Chunked Processing**: Audio files are processed in configurable chunks for better analysis

## API Endpoints

### Model Status
- **GET** `/audio/model-status`
- Returns the current status of the model loading

### Model Information
- **GET** `/audio/model-info`
- Returns detailed information about the loaded model including class mapping

### Audio Analysis
- **POST** `/audio/analyze-audio`
- Analyzes uploaded audio files for deepfake detection using chunked processing
- Accepts audio file uploads
- Returns detailed analysis results with per-chunk breakdown

#### Query Parameters:
- `chunk_duration` (float, default: 5.0): Duration of each chunk in seconds (1.0-30.0)
- `overlap` (float, default: 0.5): Overlap between chunks (0.0-0.9)

#### Response Format:
```json
{
  "is_deepfake": boolean,
  "overall_confidence": float,
  "model_loaded": boolean,
  "total_chunks": integer,
  "chunks": [
    {
      "chunk_index": integer,
      "start_time": float,
      "end_time": float,
      "is_ai_generated": boolean,
      "confidence": float,
      "class_probabilities": {
        "ai_generated": float,
        "real": float
      }
    }
  ],
  "summary": {
    "total_chunks": integer,
    "ai_generated_chunks": integer,
    "real_chunks": integer,
    "ai_generated_ratio": float,
    "average_confidence": float,
    "chunk_duration_seconds": float,
    "overlap_ratio": float
  }
}
```

## Class Mapping

- **Class 0**: AI Generated (Deepfake)
- **Class 1**: Real (Authentic)

## Usage in Code

### Accessing the Model

```python
from app.services.model_service import model_service

# Check if model is loaded
if model_service.is_model_loaded():
    # Get the model and feature extractor
    model = model_service.get_model()
    feature_extractor = model_service.get_feature_extractor()
    
    # Use for inference
    # audio_input = feature_extractor(audio_data, sampling_rate=16000, return_tensors="pt")
    # outputs = model(**audio_input)
```

### Chunked Audio Processing

```python
import librosa
import numpy as np
import torch

# Load audio
audio, sample_rate = librosa.load(audio_file, sr=16000)

# Process in chunks
chunk_duration = 5.0  # seconds
chunk_samples = int(chunk_duration * sample_rate)
overlap = 0.5
step_samples = chunk_samples - int(overlap * chunk_samples)

for i in range(0, len(audio) - chunk_samples + 1, step_samples):
    chunk_audio = audio[i:i + chunk_samples]
    
    # Prepare input
    inputs = feature_extractor(chunk_audio, sampling_rate=sample_rate, return_tensors="pt")
    
    # Run inference
    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probabilities, dim=-1).item()
        
        # Class 0 = AI generated, Class 1 = Real
        is_ai_generated = predicted_class == 0
```

### Error Handling

```python
try:
    model = model_service.get_model()
except RuntimeError as e:
    # Handle case where model is not loaded
    print(f"Model not available: {e}")
```

## Dependencies

The following packages have been added to `requirements.txt`:
- `torch==2.7.1`
- `transformers==4.53.2`
- `librosa==0.10.1`

## Installation

1. Install the new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. The model will be automatically downloaded on first use.

## Testing

Run the test scripts to verify functionality:

```bash
# Test basic model loading
python test_model_loading.py

# Test chunked audio analysis
python test_audio_analysis.py
```

## Server Startup

The model loading is integrated into the FastAPI startup event:

```python
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")
    
    # Load the audio classification model
    try:
        model_service.load_model()
        logger.info("Audio classification model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load audio classification model: {str(e)}", exc_info=True)
```

## Chunked Processing Details

### Why Chunked Processing?

1. **Memory Efficiency**: Large audio files can be processed without loading everything into memory
2. **Better Analysis**: Different parts of audio may have different characteristics
3. **Configurable**: Users can adjust chunk size and overlap based on their needs
4. **Detailed Results**: Provides per-chunk analysis for better understanding

### Parameters

- **chunk_duration**: Length of each audio chunk in seconds (1-30 seconds)
- **overlap**: Percentage of overlap between consecutive chunks (0-90%)
- **sample_rate**: Audio is resampled to 16kHz for model compatibility

### Processing Logic

1. Audio file is loaded and resampled to 16kHz
2. Audio is divided into chunks with specified duration and overlap
3. Each chunk is processed through the model
4. Results are aggregated to determine overall classification
5. Final classification is based on majority of chunks (>50% AI-generated = deepfake)

## Notes

- The model is loaded asynchronously during server startup
- If model loading fails, the server will still start but audio analysis endpoints will return errors
- The model is cached in memory for efficient inference
- Model files are downloaded to the Hugging Face cache directory on first use
- Audio processing uses librosa for robust audio handling
- Chunked processing allows for analysis of audio files of any length

## Troubleshooting

### Model Loading Fails
1. Check internet connection (required for first download)
2. Verify sufficient disk space for model files
3. Check Python environment and dependencies
4. Review application logs for detailed error messages

### Memory Issues
- The model requires significant RAM (~1-2GB)
- Consider running on a machine with adequate memory
- Monitor memory usage during model loading
- Chunked processing helps manage memory usage for large files

### Performance
- Model loading may take 30-60 seconds on first run
- Subsequent startups will be faster due to caching
- Chunked processing may take longer for large files but provides better analysis
- Consider implementing model loading in a background thread for production

### Audio Processing Issues
- Ensure audio files are in supported formats (WAV, MP3, etc.)
- Large files may take time to process due to chunking
- Adjust chunk_duration and overlap parameters for optimal performance 