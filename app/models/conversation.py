# app/models/conversation.py
"""
Modèles Pydantic pour les conversations avec l'Agent IA
Gère l'historique des échanges entre prospects et l'agent conversationnel
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Rôle de l'émetteur d'un message"""
    system = "system"      # Message système (instructions pour l'IA)
    user = "user"          # Message du prospect
    assistant = "assistant"  # Message de l'Agent IA
    function = "function"  # Résultat d'un appel de fonction/tool


class ConversationStatus(str, Enum):
    """Statut d'une conversation"""
    active = "active"          # Conversation en cours
    completed = "completed"    # Conversation terminée avec succès (lead créé)
    abandoned = "abandoned"    # Conversation abandonnée par l'utilisateur
    failed = "failed"         # Conversation échouée (erreur technique)


class MessageBase(BaseModel):
    """Modèle de base pour un message"""
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=5000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Données additionnelles


class Message(MessageBase):
    """Message complet avec métadonnées"""
    id: str
    conversation_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageAdd(BaseModel):
    """Modèle pour ajouter un message à une conversation"""
    content: str = Field(..., min_length=1, max_length=5000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ConversationBase(BaseModel):
    """Modèle de base pour une conversation"""
    # Identification du prospect
    prospect_name: Optional[str] = Field(None, max_length=200)
    prospect_phone: Optional[str] = Field(None, pattern=r'^(\+212|0)[5-7]\d{8}$')
    prospect_email: Optional[str] = Field(None, max_length=255)
    
    # Statut de la conversation
    status: ConversationStatus = ConversationStatus.active
    
    # Contexte extrait pendant la conversation
    extracted_criteria: Optional[Dict[str, Any]] = Field(default_factory=dict)
    """
    Exemple de extracted_criteria:
    {
        "budget_min": 3000000,
        "budget_max": 5000000,
        "cities": ["Casablanca", "Rabat"],
        "property_types": ["villa", "house"],
        "bedrooms": 4,
        "must_have_pool": true
    }
    """
    
    # Score de qualification calculé
    qualification_score: Optional[int] = Field(None, ge=0, le=100)
    
    # Référence au lead créé
    lead_id: Optional[str] = None  # Rempli quand la conversation génère un lead
    
    # Métriques
    message_count: int = 0
    duration_seconds: Optional[int] = None  # Durée totale en secondes


class ConversationCreate(BaseModel):
    """Modèle pour créer une nouvelle conversation"""
    prospect_name: Optional[str] = Field(None, max_length=200)
    prospect_phone: Optional[str] = Field(None, pattern=r'^(\+212|0)[5-7]\d{8}$')
    prospect_email: Optional[str] = Field(None, max_length=255)
    
    # Message initial optionnel
    initial_message: Optional[str] = Field(None, max_length=5000)


class ConversationUpdate(BaseModel):
    """Modèle pour mettre à jour une conversation"""
    prospect_name: Optional[str] = Field(None, max_length=200)
    prospect_phone: Optional[str] = Field(None, pattern=r'^(\+212|0)[5-7]\d{8}$')
    prospect_email: Optional[str] = Field(None, max_length=255)
    
    status: Optional[ConversationStatus] = None
    extracted_criteria: Optional[Dict[str, Any]] = None
    qualification_score: Optional[int] = Field(None, ge=0, le=100)
    lead_id: Optional[str] = None
    duration_seconds: Optional[int] = None


class ConversationList(BaseModel):
    """Modèle simplifié pour lister les conversations"""
    id: str
    prospect_name: Optional[str]
    prospect_phone: Optional[str]
    status: ConversationStatus
    message_count: int
    qualification_score: Optional[int]
    lead_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class Conversation(ConversationBase):
    """Modèle complet d'une conversation"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationWithMessages(Conversation):
    """Conversation avec son historique de messages"""
    messages: list[Message] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    """Résumé d'une conversation pour analytics"""
    id: str
    status: ConversationStatus
    prospect_name: Optional[str]
    message_count: int
    qualification_score: Optional[int]
    lead_created: bool
    duration_seconds: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]