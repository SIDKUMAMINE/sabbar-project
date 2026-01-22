"""
Client Supabase pour SABBAR
"""
from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """Singleton pour le client Supabase"""
    
    _client: Client = None
    _admin_client: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Retourne l'instance du client Supabase"""
        if cls._client is None:
            cls._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
        return cls._client
    
    @classmethod
    def get_admin_client(cls) -> Client:
        """Retourne le client avec service key (admin)"""
        if cls._admin_client is None:
            cls._admin_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return cls._admin_client


# Instances globales
supabase = SupabaseClient.get_client()
supabase_admin = SupabaseClient.get_admin_client()