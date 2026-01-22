# app/models/__init__.py
"""
Modèles Pydantic pour l'API SABBAR

Modules implémentés:
- Property : Annonces immobilières (COMPLET)
- Lead : Prospects qualifiés (NOUVEAU)
- Conversation : Historique IA (NOUVEAU)

À venir:
- User : Agents immobiliers
"""

# ====================================
# PROPERTY MODELS (Implémenté)
# ====================================
from .property import (
    PropertyType,
    TransactionType,
    PropertyBase,
    PropertyCreate,
    PropertyUpdate,
    PropertyList,
    Property
)

# ====================================
# LEAD MODELS (Nouveau)
# ====================================
from .lead import (
    LeadStatus,
    LeadSource,
    LeadPriority,
    LeadBase,
    LeadCreate,
    LeadUpdate,
    LeadList,
    Lead,
    LeadWithMatches
)

# ====================================
# CONVERSATION MODELS (Nouveau)
# ====================================
from .conversation import (
    MessageRole,
    ConversationStatus,
    MessageBase,
    Message,
    MessageAdd,
    ConversationBase,
    ConversationCreate,
    ConversationUpdate,
    ConversationList,
    Conversation,
    ConversationWithMessages,
    ConversationSummary
)

# ====================================
# EXPORTS
# ====================================
__all__ = [
    # Property
    "PropertyType",
    "TransactionType",
    "PropertyBase",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyList",
    "Property",
    
    # Lead
    "LeadStatus",
    "LeadSource",
    "LeadPriority",
    "LeadBase",
    "LeadCreate",
    "LeadUpdate",
    "LeadList",
    "Lead",
    "LeadWithMatches",
    
    # Conversation
    "MessageRole",
    "ConversationStatus",
    "MessageBase",
    "Message",
    "MessageAdd",
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationList",
    "Conversation",
    "ConversationWithMessages",
    "ConversationSummary",
]