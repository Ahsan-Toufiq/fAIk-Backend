# Audio API Testing Examples

This document provides examples of how to test the audio analysis API endpoints.

## Prerequisites

1. Make sure the server is running:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Endpoints

### 1. Check Model Status
```bash
curl -X GET "http://localhost:8000/audio/model-status"
```

**Expected Response:**
```json
{
  "model_loaded": true,
  "model_name": "mo-thecreator/Deepfake-audio-detection"
}
```

### 2. Get Model Information
```bash
curl -X GET "http://localhost:8000/audio/model-info"
```

**Expected Response:**
```json
{
  "model_name": "mo-thecreator/Deepfake-audio-detection",
  "model_type": "Wav2Vec2ForSequenceClassification",
  "feature_extractor_type": "Wav2Vec2FeatureExtractor",
  "num_classes": 2,
  "class_mapping": {
    "0": "AI Generated",
    "1": "Real"
  }
}
```

### 3. Analyze Audio File

#### Basic Analysis (Default Parameters)
```bash
curl -X POST "http://localhost:8000/audio/analyze-audio" \
  -F "audio_file=@/path/to/your/audio_file.wav"
```

#### Custom Chunk Parameters
```bash
curl -X POST "http://localhost:8000/audio/analyze-audio?chunk_duration=3.0&overlap=0.3" \
  -F "audio_file=@/path/to/your/audio_file.wav"
```

**Important Notes:**
- Use `@` symbol before the file path to upload the actual file
- Don't include `-H "Content-Type: multipart/form-data"` - curl sets this automatically
- Replace `/path/to/your/audio_file.wav` with the actual path to your audio file

**Example with your file:**
```bash
curl -X POST "http://localhost:8000/audio/analyze-audio?chunk_duration=3.0&overlap=0.3" \
  -F "audio_file=@/home/syed-hassan-ul-haq/repos/AI_detection-Wave2Vec2/deepfake_audio/for-norm_file33607.mp3.wav_16k.wav_norm.wav_mono.wav_silence.wav"
```

**Parameters:**
- `chunk_duration`: Duration of each chunk in seconds (1.0-30.0, default: 5.0)
- `overlap`: Overlap between chunks (0.0-0.9, default: 0.5)

**Expected Response:**
```json
{
  "is_deepfake": false,
  "overall_confidence": 0.85,
  "model_loaded": true,
  "total_chunks": 5,
  "chunks": [
    {
      "chunk_index": 0,
      "start_time": 0.0,
      "end_time": 5.0,
      "is_ai_generated": false,
      "confidence": 0.92,
      "class_probabilities": {
        "ai_generated": 0.08,
        "real": 0.92
      }
    }
  ],
  "summary": {
    "total_chunks": 5,
    "ai_generated_chunks": 1,
    "real_chunks": 4,
    "ai_generated_ratio": 0.2,
    "average_confidence": 0.85,
    "chunk_duration_seconds": 5.0,
    "overlap_ratio": 0.5
  }
}
```

## Python Testing Scripts

### 1. Test Model Loading
```bash
python test_model_loading.py
```

### 2. Test Chunked Audio Analysis
```bash
python test_audio_analysis.py
```

### 3. Test API Endpoints
```bash
python test_audio_api.py
```

## Using Python Requests

```python
import requests

# Test model status
response = requests.get("http://localhost:8000/audio/model-status")
print(response.json())

# Test audio analysis
with open("audio_file.wav", "rb") as f:
    files = {"audio_file": ("audio.wav", f, "audio/wav")}
    params = {"chunk_duration": 3.0, "overlap": 0.3}
    
    response = requests.post(
        "http://localhost:8000/audio/analyze-audio",
        files=files,
        params=params
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Is deepfake: {result['is_deepfake']}")
        print(f"Confidence: {result['overall_confidence']}")
        print(f"Total chunks: {result['total_chunks']}")
```

## Common Issues and Solutions

### 1. Model Not Loaded
**Error:** `503 Service Unavailable - Audio classification model is not loaded`
**Solution:** Wait for the server to fully start up (model loading takes 30-60 seconds on first run)

### 2. Invalid File Format
**Error:** `500 Internal Server Error - Error analyzing audio file`
**Solution:** Ensure the audio file is in a supported format (WAV, MP3, etc.)

### 3. File Too Large
**Error:** `413 Payload Too Large`
**Solution:** Use smaller audio files or increase server limits

### 4. Validation Error
**Error:** `422 Unprocessable Entity - Validation error`
**Solution:** Ensure you're sending the file as `multipart/form-data` with the correct field name `audio_file`

### 5. File Upload Error
**Error:** `Expected UploadFile, received: <class 'str'>`
**Solution:** Use `@` symbol before file path in curl: `-F "audio_file=@/path/to/file.wav"`

## Performance Notes

- **First Run**: Model loading may take 30-60 seconds
- **Subsequent Runs**: Model is cached and loads much faster
- **Large Files**: Processing time depends on file size and chunk parameters
- **Memory Usage**: Model requires ~1-2GB RAM

## Supported Audio Formats

- WAV
- MP3
- FLAC
- OGG
- And other formats supported by librosa

## Chunking Strategy

- **Small chunks (1-3s)**: Better for detecting short AI-generated segments
- **Large chunks (5-10s)**: Better for overall classification
- **Overlap**: Higher overlap (0.7-0.9) provides smoother analysis
- **No overlap (0.0)**: Faster processing but may miss transitions 