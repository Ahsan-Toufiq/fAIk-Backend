from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
import logging

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self):
        self.model = None
        self.feature_extractor = None
        self.model_name = "mo-thecreator/Deepfake-audio-detection"
        self.is_loaded = False
    
    def load_model(self):
        """Load the audio classification model and feature extractor"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            self.model = AutoModelForAudioClassification.from_pretrained(self.model_name)
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_name)
            
            self.is_loaded = True
            logger.info(f"Model and feature extractor loaded successfully for: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {str(e)}", exc_info=True)
            raise
    
    def get_model(self):
        """Get the loaded model"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return self.model
    
    def get_feature_extractor(self):
        """Get the loaded feature extractor"""
        if not self.is_loaded:
            raise RuntimeError("Feature extractor not loaded. Call load_model() first.")
        return self.feature_extractor
    
    def is_model_loaded(self):
        """Check if the model is loaded"""
        return self.is_loaded

# Global instance
model_service = ModelService() 