"""Router API principal v1"""
from fastapi import APIRouter
from app.api.v1.endpoints import properties, ai, leads, conversations

# Créer le router principal
api_router = APIRouter()

# ==================== PROPERTIES ====================
api_router.include_router(
    properties.router, 
    prefix="/properties", 
    tags=["Properties"]
)

# ==================== LEADS ====================
api_router.include_router(
    leads.router, 
    prefix="/leads", 
    tags=["Leads"]
)

# ==================== CONVERSATIONS ====================
api_router.include_router(
    conversations.router, 
    prefix="/conversations", 
    tags=["Conversations"]
)

# ==================== AI AGENT ====================
api_router.include_router(
    ai.router, 
    prefix="/ai", 
    tags=["AI Agent"]
)   