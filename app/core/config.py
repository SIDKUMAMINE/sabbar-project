"""Configuration de l'application SABBAR"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Paramètres de configuration"""
    
    # Application
    APP_NAME: str = "SABBAR"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS - URLs autorisées
    CORS_ORIGINS: str = "http://localhost:8000,http://localhost:3000,http://127.0.0.1:3000"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Hugging Face API (pour l'agent IA)
    HUGGINGFACE_API_TOKEN: str  # ⬅️ CHANGÉ
    
    # Modèle LLM à utiliser
    LLM_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"  # ⬅️ AJOUTÉ
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 512
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Transforme CORS_ORIGINS en liste"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Instance globale
settings = Settings()