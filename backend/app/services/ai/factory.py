import os
from app.services.ai.base import BaseAIPredictor
from app.services.ai.gemini import GeminiPredictor
from app.core.config import settings
from app.services.ai.groq import GroqPredictor

def get_ai_predictor() -> BaseAIPredictor:
    """Çevre değişkenine göre doğru AI sağlayıcısını döndürür."""
    provider = settings.AI_PROVIDER.lower()
    
    if provider == "gemini":
        return GeminiPredictor()
    elif provider == "groq":
        return GroqPredictor()
    # elif provider == "openai":
    #     return OpenAIPredictor()
    
    return GeminiPredictor()  # Default fallback