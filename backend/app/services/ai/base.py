from abc import ABC, abstractmethod

class BaseAIPredictor(ABC):
    """Tüm AI sağlayıcıları için ortak kontrat."""
    
    @abstractmethod
    async def generate_insight_async(self, prediction_data: dict) -> str:
        pass

    @abstractmethod
    async def generate_tennis_insight_async(self, prediction_data: dict) -> str:
        pass