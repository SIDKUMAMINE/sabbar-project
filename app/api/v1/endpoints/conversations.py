"""
Endpoints API pour l'agent de qualification des leads.
6 endpoints professionnels pour gérer le cycle de vie complet des conversations.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from app.ai.agent import QualificationAgent  # ✅ CORRIGÉ ICI
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# MODÈLES PYDANTIC (Request/Response)
# ============================================================================

class StartConversationRequest(BaseModel):
    """Requête pour démarrer une nouvelle conversation."""
    initial_message: Optional[str] = Field(
        None,
        description="Message initial de l'utilisateur (optionnel)",
        example="Je cherche un appartement à Casablanca"
    )
    user_id: Optional[str] = Field(
        None,
        description="ID de l'agent immobilier assigné (optionnel)"
    )


class StartConversationResponse(BaseModel):
    """Réponse au démarrage d'une conversation."""
    conversation_id: str = Field(..., description="ID unique de la conversation")
    response: str = Field(..., description="Première réponse de l'assistant")
    status: str = Field(..., description="Statut de la conversation (active)")
    qualification_score: int = Field(..., description="Score initial (0-100)")


class ContinueConversationRequest(BaseModel):
    """Requête pour continuer une conversation."""
    user_message: str = Field(
        ...,
        description="Message de l'utilisateur",
        min_length=1,
        max_length=1000,
        example="Mon budget est entre 1,5 et 2 millions"
    )


class ContinueConversationResponse(BaseModel):
    """Réponse à la continuation d'une conversation."""
    conversation_id: str
    response: str = Field(..., description="Réponse de l'assistant")
    qualification_score: int = Field(..., description="Score actuel (0-100)")
    lead_quality: str = Field(..., description="Qualité du lead (hot/warm/cold)")
    should_create_lead: bool = Field(..., description="Lead doit être créé ?")
    conversation_complete: bool = Field(..., description="Conversation terminée ?")
    properties_shown: bool = Field(..., description="Propriétés affichées ?")
    matched_properties_count: int = Field(..., description="Nombre de propriétés trouvées")
    lead_id: Optional[str] = Field(None, description="ID du lead créé (si applicable)")
    criteria_extracted: Dict[str, bool] = Field(
        ...,
        description="État d'extraction des critères"
    )


class ConversationStateResponse(BaseModel):
    """État complet d'une conversation."""
    conversation_id: str
    messages: list = Field(..., description="Historique des messages")
    qualification_score: int
    lead_quality: str
    criteria: Dict[str, Any] = Field(..., description="Critères extraits")
    contact_info: Dict[str, Optional[str]] = Field(..., description="Infos de contact")
    status: str = Field(..., description="active ou completed")
    lead_id: Optional[str] = None


class EndConversationRequest(BaseModel):
    """Requête pour terminer une conversation."""
    reason: str = Field(
        "completed",
        description="Raison de la fin (completed, abandoned, error)"
    )


class EndConversationResponse(BaseModel):
    """Résumé après fin de conversation."""
    conversation_id: str
    status: str
    qualification_score: int
    lead_quality: str
    lead_created: bool
    lead_id: Optional[str] = None
    messages_count: int
    summary: str = Field(..., description="Résumé de la conversation")


class AgentStatsResponse(BaseModel):
    """Statistiques globales de l'agent."""
    active_conversations_count: int = Field(
        ...,
        description="Nombre de conversations actives en cache"
    )


# ============================================================================
# ENDPOINT 1 : START - Démarrer une conversation
# ============================================================================

@router.post(
    "/start",
    response_model=StartConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="🚀 Démarrer une conversation",
    description="""
    Démarre une nouvelle conversation de qualification avec l'agent IA.
    
    **Cas d'usage :**
    - Nouveau prospect arrive sur le site
    - Click sur "Parler à un agent"
    - WhatsApp Business API
    
    **Réponse :**
    - Conversation ID unique
    - Message de bienvenue personnalisé
    - Score initial (généralement 0-15)
    
    **Exemple :**
    ```json
    {
      "initial_message": "Je cherche un appartement à Casablanca"
    }
    ```
    """,
    tags=["Agent IA"]
)
async def start_conversation(
    request: StartConversationRequest,
    supabase=Depends(get_supabase_client)
):
    """
    Démarre une nouvelle conversation de qualification.
    
    Args:
        request: Requête avec message initial (optionnel)
        supabase: Client Supabase injecté
        
    Returns:
        Réponse avec conversation_id et première réponse de l'agent
        
    Raises:
        HTTPException: Si erreur lors de la création
    """
    try:
        logger.info("📞 Nouvelle conversation demandée")
        
        # Initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        # Démarrage de la conversation
        result = await agent.start_conversation(
            initial_message=request.initial_message,
            user_id=request.user_id
        )
        
        logger.info(f"✅ Conversation {result['conversation_id']} créée avec succès")
        
        return StartConversationResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du démarrage de la conversation: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2 : CONTINUE - Continuer une conversation
# ============================================================================

@router.post(
    "/continue/{conversation_id}",
    response_model=ContinueConversationResponse,
    summary="💬 Continuer une conversation",
    description="""
    Envoie un nouveau message à l'agent dans une conversation existante.
    
    **Le workflow complet :**
    1. Analyse du message (extraction critères)
    2. Calcul du score de qualification
    3. Recherche de propriétés (si critères suffisants)
    4. Génération de la réponse IA
    5. Création automatique du lead (si qualifié)
    
    **Score de qualification :**
    - Budget défini: +25 points
    - Localisation définie: +20 points
    - Type de bien défini: +15 points
    - Délai de projet: +10 points
    - Contact complet: +15 points
    - Critères spécifiques: +10 points
    - Engagement: +5 points
    
    **Lead créé automatiquement si :**
    - Score ≥ 50 points
    - Contact complet (nom + téléphone)
    """,
    tags=["Agent IA"]
)
async def continue_conversation(
    conversation_id: str,
    request: ContinueConversationRequest,
    supabase=Depends(get_supabase_client)
):
    """
    Continue une conversation existante avec un nouveau message.
    
    Args:
        conversation_id: ID de la conversation
        request: Requête avec le message utilisateur
        supabase: Client Supabase injecté
        
    Returns:
        Réponse de l'agent avec métadonnées de qualification
        
    Raises:
        HTTPException: Si conversation non trouvée ou erreur de traitement
    """
    try:
        logger.info(f"💬 Message reçu pour conversation {conversation_id}")
        
        # Initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        # Traitement du message
        result = await agent.continue_conversation(
            conversation_id=conversation_id,
            user_message=request.user_message
        )
        
        logger.info(
            f"✅ Message traité - Score: {result['qualification_score']}/100, "
            f"Qualité: {result['lead_quality']}"
        )
        
        return ContinueConversationResponse(**result)
        
    except ValueError as e:
        logger.warning(f"⚠️ Conversation {conversation_id} non trouvée")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} non trouvée"
        )
    except Exception as e:
        logger.error(f"❌ Erreur lors de la continuation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement du message: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3 : GET CONVERSATION - Récupérer l'état complet
# ============================================================================

@router.get(
    "/conversation/{conversation_id}",
    response_model=ConversationStateResponse,
    summary="📊 Récupérer l'état d'une conversation",
    description="""
    Récupère l'état complet d'une conversation en cours ou terminée.
    
    **Informations retournées :**
    - Historique complet des messages
    - Score de qualification actuel
    - Tous les critères extraits (budget, localisation, etc.)
    - Informations de contact
    - Statut (active ou completed)
    - ID du lead créé (si applicable)
    
    **Cas d'usage :**
    - Dashboard agent immobilier
    - Reprise de conversation après déconnexion
    - Analytics et reporting
    - Debugging
    """,
    tags=["Agent IA"]
)
async def get_conversation_state(
    conversation_id: str,
    supabase=Depends(get_supabase_client)
):
    """
    Récupère l'état complet d'une conversation.
    
    Args:
        conversation_id: ID de la conversation
        supabase: Client Supabase injecté
        
    Returns:
        État complet de la conversation
        
    Raises:
        HTTPException: Si conversation non trouvée
    """
    try:
        logger.info(f"📊 Récupération état conversation {conversation_id}")
        
        # Initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        # Récupération de l'état
        state = await agent.get_conversation_state(conversation_id)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} non trouvée"
            )
        
        logger.info(f"✅ État récupéré - Score: {state['qualification_score']}/100")
        
        return ConversationStateResponse(**state)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération état: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'état: {str(e)}"
        )


# ============================================================================
# ENDPOINT 4 : END - Terminer une conversation
# ============================================================================

@router.post(
    "/end/{conversation_id}",
    response_model=EndConversationResponse,
    summary="🏁 Terminer une conversation",
    description="""
    Termine une conversation et génère un résumé complet.
    
    **Actions effectuées :**
    1. Génération d'un résumé de la conversation
    2. Création du lead (si qualifié et pas encore créé)
    3. Marquage de la conversation comme terminée
    4. Nettoyage du cache
    
    **Raisons possibles :**
    - `completed`: Conversation terminée normalement
    - `abandoned`: Prospect a quitté
    - `error`: Erreur technique
    
    **Le résumé contient :**
    - Besoins principaux du prospect
    - Score de qualification final
    - Lead créé ou non
    - Nombre de messages échangés
    """,
    tags=["Agent IA"]
)
async def end_conversation(
    conversation_id: str,
    request: EndConversationRequest = EndConversationRequest(),
    supabase=Depends(get_supabase_client)
):
    """
    Termine une conversation.
    
    Args:
        conversation_id: ID de la conversation
        request: Requête avec raison de fin (optionnel)
        supabase: Client Supabase injecté
        
    Returns:
        Résumé de la conversation
        
    Raises:
        HTTPException: Si conversation non trouvée
    """
    try:
        logger.info(f"🏁 Fin de conversation {conversation_id} - Raison: {request.reason}")
        
        # Initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        # Fin de la conversation
        summary = await agent.end_conversation(
            conversation_id=conversation_id,
            reason=request.reason
        )
        
        if "error" in summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=summary["error"]
            )
        
        logger.info(f"✅ Conversation terminée - Lead créé: {summary['lead_created']}")
        
        return EndConversationResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur fin conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la fin de conversation: {str(e)}"
        )


# ============================================================================
# ENDPOINT 5 : STATS - Statistiques de l'agent
# ============================================================================

@router.get(
    "/stats",
    response_model=AgentStatsResponse,
    summary="📈 Statistiques de l'agent",
    description="""
    Récupère des statistiques sur l'état actuel de l'agent.
    
    **Métriques actuelles :**
    - Nombre de conversations actives en cache
    
    **Métriques futures :**
    - Taux de conversion (conversations → leads)
    - Temps moyen de conversation
    - Score moyen de qualification
    - Distribution hot/warm/cold
    - Taux d'abandon
    
    **Cas d'usage :**
    - Dashboard de monitoring
    - Alertes (trop de conversations actives)
    - Performance tracking
    """,
    tags=["Agent IA"]
)
async def get_agent_stats(supabase=Depends(get_supabase_client)):
    """
    Récupère les statistiques de l'agent.
    
    Args:
        supabase: Client Supabase injecté
        
    Returns:
        Statistiques globales
    """
    try:
        logger.info("📈 Récupération des statistiques")
        
        # Initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        # Récupération des stats
        active_count = agent.get_active_conversations_count()
        
        logger.info(f"✅ Stats récupérées - {active_count} conversations actives")
        
        return AgentStatsResponse(
            active_conversations_count=active_count
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des stats: {str(e)}"
        )


# ============================================================================
# ENDPOINT 6 : HEALTH - Health check
# ============================================================================

@router.get(
    "/health",
    summary="❤️ Health check de l'agent",
    description="""
    Vérifie que l'agent IA est opérationnel.
    
    **Vérifications effectuées :**
    - Initialisation de l'agent
    - Connexion Supabase
    - Disponibilité Hugging Face API (implicite)
    
    **Statuts possibles :**
    - `healthy`: Tout fonctionne
    - `unhealthy`: Problème détecté
    
    **Cas d'usage :**
    - Monitoring uptime
    - Health checks Kubernetes/Docker
    - Load balancer checks
    """,
    tags=["Agent IA", "health"]
)
async def health_check(supabase=Depends(get_supabase_client)):
    """
    Vérifie que l'agent IA est opérationnel.
    
    Args:
        supabase: Client Supabase injecté
        
    Returns:
        Statut de santé
    """
    try:
        # Test d'initialisation de l'agent
        agent = QualificationAgent(supabase)
        
        logger.info("✅ Health check OK")
        
        return {
            "status": "healthy",
            "service": "agent_ia",
            "message": "Agent IA opérationnel",
            "model": agent.model,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Health check échoué: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "agent_ia",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }