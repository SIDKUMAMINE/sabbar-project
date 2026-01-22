# app/crud/__init__.py
"""
Couche CRUD pour l'API SABBAR

Modules CRUD:
- Property: Annonces immobilières (COMPLET)
- Lead: Prospects qualifiés (NOUVEAU)
- Conversation: Sessions IA et messages (NOUVEAU)
"""

from .property import PropertyCRUD, get_property_crud
from .lead import LeadCRUD, get_lead_crud
from .conversation import ConversationCRUD, get_conversation_crud
from .ai_conversation import AIConversationCRUD, get_ai_conversation_crud  
__all__ = [
    # Property CRUD
    "PropertyCRUD",
    "get_property_crud",
    
    # Lead CRUD
    "LeadCRUD",
    "get_lead_crud",
    
    # Conversation CRUD
    "ConversationCRUD",
    "get_conversation_crud",
]