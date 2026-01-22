"""
Client Supabase pour l'application.
Gère la connexion à la base de données Supabase.

Ce module exporte plusieurs noms pour compatibilité :
- get_supabase_client (nouveau code)
- get_supabase (ancien code)
- SupabaseClient (classe)
"""
from supabase import create_client, Client
from functools import lru_cache
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Classe wrapper pour le client Supabase.
    Permet une gestion plus flexible de la connexion.
    """
    
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Retourne l'instance du client Supabase (Singleton).
        
        Returns:
            Client Supabase configuré
        """
        if cls._instance is None:
            try:
                logger.info("🔌 Initialisation du client Supabase...")
                
                cls._instance = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY
                )
                
                logger.info("✅ Client Supabase initialisé avec succès")
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'initialisation Supabase: {str(e)}")
                raise
        
        return cls._instance


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retourne une instance du client Supabase.
    
    Utilise @lru_cache pour créer une seule instance réutilisée
    (pattern Singleton pour les performances).
    
    Nom utilisé par les NOUVEAUX endpoints (agent IA).
    
    Returns:
        Client Supabase configuré
        
    Raises:
        Exception: Si la configuration Supabase est invalide
    """
    return SupabaseClient.get_client()


def get_supabase() -> Client:
    """
    Retourne une instance du client Supabase.
    
    Nom utilisé par les ANCIENS endpoints (properties, leads, etc.).
    
    Alias de get_supabase_client() pour compatibilité avec le code existant.
    
    Returns:
        Client Supabase configuré
    """
    return get_supabase_client()


# Alias pour l'injection de dépendances FastAPI
def get_db() -> Client:
    """
    Dependency pour FastAPI.
    Permet d'injecter le client Supabase dans les endpoints.
    
    Usage:
        @app.get("/endpoint")
        async def my_endpoint(db: Client = Depends(get_db)):
            # Utiliser db ici
            
    Returns:
        Client Supabase
    """
    return get_supabase_client()


# Pour compatibilité avec différents styles d'import
__all__ = [
    "SupabaseClient",
    "get_supabase_client",
    "get_supabase",
    "get_db"
]