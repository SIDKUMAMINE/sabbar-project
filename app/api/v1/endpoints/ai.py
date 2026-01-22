"""Endpoints pour l'agent IA conversationnel"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.ai.agent import SABBARAgent
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ✅ Ne PAS instancier ici, utiliser une factory
_agent_instance = None


def get_agent() -> SABBARAgent:
    """Factory pour obtenir l'instance de l'agent (lazy loading)"""
    global _agent_instance
    if _agent_instance is None:
        logger.info("🤖 Initialisation de l'agent IA...")
        _agent_instance = SABBARAgent()
    return _agent_instance


class ChatRequest(BaseModel):
    """Requête de chat"""
    message: str
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Réponse du chat"""
    response: str
    conversation_id: str
    extracted_criteria: Dict[str, Any]
    qualification_score: int


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Envoyer un message à l'agent IA
    
    - **message**: Message de l'utilisateur
    - **conversation_id**: ID de conversation (optionnel)
    - **history**: Historique des messages (optionnel)
    """
    try:
        logger.info(f"📩 Message reçu : {request.message}")
        
        # Obtenir l'agent (lazy loading)
        agent = get_agent()
        
        # Appeler l'agent
        result = agent.chat(
            user_message=request.message,
            conversation_history=request.history or []
        )
        
        # Générer un ID de conversation si nécessaire
        conversation_id = request.conversation_id or f"conv_{hash(request.message)}"
        
        return ChatResponse(
            response=result["response"],
            conversation_id=conversation_id,
            extracted_criteria=result["extracted_criteria"],
            qualification_score=result["qualification_score"]
        )
    
    except Exception as e:
        logger.error(f"❌ Erreur dans le chat : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Vérifier que l'agent IA fonctionne"""
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "agent": "SABBAR AI",
            "model": agent.model
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }