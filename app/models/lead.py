# app/models/lead.py
"""
Modèles Pydantic pour les leads (prospects)
Un lead représente un prospect qualifié par l'Agent IA
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import re


# ==========================================
# ENUMS - Définis EN PREMIER
# ==========================================

class LeadStatus(str, Enum):
    """Statut du lead dans le pipeline de vente"""
    new = "new"                    # Nouveau lead non traité
    contacted = "contacted"        # Lead contacté par l'agent
    qualified = "qualified"        # Lead qualifié (critères validés)
    interested = "interested"      # Lead intéressé
    meeting_scheduled = "meeting_scheduled"  # RDV pris
    proposal_sent = "proposal_sent"          # Proposition envoyée
    negotiation = "negotiation"    # En négociation
    converted = "converted"        # Converti en client
    lost = "lost"                  # Perdu
    unqualified = "unqualified"    # Non qualifié
    archived = "archived"          # Archivé


class LeadSource(str, Enum):
    """Source d'acquisition du lead"""
    agent_ia = "agent_ia"          # Qualifié par l'Agent IA (principal)
    chatbot = "chatbot"            # Chatbot web
    website = "website"            # Formulaire site web
    web_form = "web_form"          # Formulaire site web
    phone = "phone"                # Appel téléphonique
    email = "email"                # Email direct
    referral = "referral"          # Référence/recommandation
    social_media = "social_media"  # Réseaux sociaux
    walk_in = "walk_in"           # Visite directe agence
    other = "other"                # Autre


class LeadPriority(str, Enum):
    """Niveau de priorité du lead"""
    low = "low"                    # Basse priorité
    medium = "medium"              # Priorité moyenne
    high = "high"                  # Haute priorité
    urgent = "urgent"              # Urgent (à traiter immédiatement)


class TransactionType(str, Enum):
    """Type de transaction immobilière (VALEURS EN FRANÇAIS)"""
    VENTE = "vente"
    LOCATION = "location"
    LOCATION_VACANCES = "location_vacances"


# ==========================================
# MODÈLES PYDANTIC
# ==========================================

class LeadBase(BaseModel):
    """Modèle de base pour un lead"""
    # Informations personnelles
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: str = Field(..., pattern=r'^(\+212|0)[5-7]\d{8}$')  # Format marocain
    
    # Statut et priorité
    status: LeadStatus = LeadStatus.new
    source: LeadSource = LeadSource.agent_ia
    priority: LeadPriority = LeadPriority.medium
    
    # Critères de recherche extraits par l'IA
    budget_min: Optional[float] = Field(None, gt=0)
    budget_max: Optional[float] = Field(None, gt=0)
    preferred_cities: Optional[list[str]] = Field(default_factory=list)
    preferred_districts: Optional[list[str]] = Field(default_factory=list)
    property_types: Optional[list[str]] = Field(default_factory=list)  # apartment, villa, etc.
    
    # ✅ Type de transaction en FRANÇAIS
    transaction_type: Optional[TransactionType] = None
    
    # Caractéristiques souhaitées
    min_area: Optional[float] = Field(None, gt=0)
    max_area: Optional[float] = None
    min_bedrooms: Optional[int] = Field(None, ge=0)
    min_bathrooms: Optional[int] = Field(None, ge=0)
    
    # Équipements requis
    must_have_parking: bool = False
    must_have_garden: bool = False
    must_have_pool: bool = False
    must_have_elevator: bool = False
    
    # Scoring et matching
    qualification_score: int = Field(default=0, ge=0, le=100)  # Score 0-100
    matched_properties: Optional[list[str]] = Field(default_factory=list)  # IDs des properties matchées
    
    # Notes et contexte
    notes: Optional[str] = Field(None, max_length=2000)
    ai_conversation_summary: Optional[str] = Field(None, max_length=1000)  # Résumé de la conversation IA
    
    # Métadonnées
    conversation_id: Optional[str] = None  # Référence à la conversation IA
    assigned_to: Optional[str] = None  # ID de l'agent immobilier assigné
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Valider le format email"""
        if v is None:
            return v
        # Regex simple pour email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Format email invalide')
        return v.lower()
    
    @field_validator('budget_max')
    @classmethod
    def validate_budget_range(cls, v: Optional[float], info) -> Optional[float]:
        """Vérifier que budget_max > budget_min"""
        budget_min = info.data.get('budget_min')
        if v is not None and budget_min is not None:
            if v < budget_min:
                raise ValueError('budget_max doit être supérieur à budget_min')
        return v


class LeadCreate(LeadBase):
    """Modèle pour créer un nouveau lead"""
    pass  # Hérite de LeadBase sans modifications


class LeadUpdate(BaseModel):
    """Modèle pour mettre à jour un lead (tous les champs optionnels)"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, pattern=r'^(\+212|0)[5-7]\d{8}$')
    
    status: Optional[LeadStatus] = None
    source: Optional[LeadSource] = None
    priority: Optional[LeadPriority] = None
    
    budget_min: Optional[float] = Field(None, gt=0)
    budget_max: Optional[float] = Field(None, gt=0)
    preferred_cities: Optional[list[str]] = None
    preferred_districts: Optional[list[str]] = None
    property_types: Optional[list[str]] = None
    transaction_type: Optional[TransactionType] = None
    
    min_area: Optional[float] = Field(None, gt=0)
    max_area: Optional[float] = None
    min_bedrooms: Optional[int] = Field(None, ge=0)
    min_bathrooms: Optional[int] = Field(None, ge=0)
    
    must_have_parking: Optional[bool] = None
    must_have_garden: Optional[bool] = None
    must_have_pool: Optional[bool] = None
    must_have_elevator: Optional[bool] = None
    
    qualification_score: Optional[int] = Field(None, ge=0, le=100)
    matched_properties: Optional[list[str]] = None
    
    notes: Optional[str] = Field(None, max_length=2000)
    ai_conversation_summary: Optional[str] = Field(None, max_length=1000)
    
    conversation_id: Optional[str] = None
    assigned_to: Optional[str] = None


class LeadList(BaseModel):
    """Modèle simplifié pour lister les leads"""
    id: str
    first_name: str
    last_name: str
    email: Optional[str]
    phone: str
    status: LeadStatus
    source: LeadSource
    priority: LeadPriority
    qualification_score: int
    budget_min: Optional[float]
    budget_max: Optional[float]
    preferred_cities: Optional[list[str]]
    transaction_type: Optional[TransactionType]
    created_at: datetime
    
    class Config:
        from_attributes = True


class Lead(LeadBase):
    """Modèle complet d'un lead avec métadonnées"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None  # Dernière date de contact
    
    class Config:
        from_attributes = True


class LeadWithMatches(Lead):
    """Lead avec les properties matchées (pour l'API)"""
    matched_property_details: Optional[list[Dict[str, Any]]] = Field(default_factory=list)