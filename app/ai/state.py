"""
État du workflow de qualification des leads.
Définit la structure de données partagée entre les nœuds du graph LangGraph.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add
import logging

logger = logging.getLogger(__name__)


class Message(TypedDict):
    """Structure d'un message dans la conversation."""
    role: str  # "user" ou "assistant"
    content: str  # Contenu du message
    timestamp: Optional[str]  # ISO timestamp


class ConversationState(TypedDict):
    """
    État global de la conversation de qualification.
    Partagé entre tous les nœuds du graph LangGraph.
    """
    
    # Conversation
    messages: Annotated[List[Message], add]  # Historique des messages (accumulé)
    current_user_message: str  # Dernier message de l'utilisateur
    assistant_response: str  # Dernière réponse de l'assistant
    
    # Informations extraites du prospect
    full_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    
    # Critères de recherche identifiés
    transaction_type: Optional[str]  # vente, location, location_vacances
    property_type: Optional[str]  # appartement, villa, etc.
    cities: List[str]  # Villes d'intérêt
    neighborhoods: List[str]  # Quartiers spécifiques
    budget_min: Optional[float]  # Budget minimum en MAD
    budget_max: Optional[float]  # Budget maximum en MAD
    bedrooms: Optional[int]  # Nombre de chambres
    surface_min: Optional[float]  # Surface minimale en m²
    amenities: List[str]  # Équipements souhaités (parking, jardin, etc.)
    
    # Contexte du projet
    timeframe: Optional[str]  # Délai du projet
    motivation: Optional[str]  # Motivation (habitation, investissement, etc.)
    
    # Méta-données de qualification
    budget_defined: bool  # Le budget est-il clairement défini ?
    location_defined: bool  # La localisation est-elle définie ?
    property_type_defined: bool  # Le type de bien est-il défini ?
    timeframe_defined: bool  # Le délai est-il défini ?
    contact_info_complete: bool  # Contact complet (nom + tél minimum) ?
    specific_criteria_count: int  # Nombre de critères spécifiques fournis
    engagement_level: int  # Niveau d'engagement (0-10)
    
    qualification_score: int  # Score calculé (0-100)
    lead_quality: str  # hot, warm, cold
    
    # Propriétés trouvées
    matched_properties: List[Dict[str, Any]]  # Propriétés correspondant aux critères
    properties_shown: bool  # Des propriétés ont-elles été présentées ?
    
    # Contrôle du workflow
    conversation_complete: bool  # Conversation terminée ?
    should_create_lead: bool  # Doit-on créer un lead ?
    lead_id: Optional[str]  # ID du lead créé (si applicable)
    
    # Notes et résumé
    conversation_notes: str  # Notes sur la conversation
    conversation_summary: str  # Résumé final


def create_initial_state() -> ConversationState:
    """
    Crée l'état initial d'une nouvelle conversation.
    
    Returns:
        État initial avec valeurs par défaut
    """
    return ConversationState(
        # Conversation
        messages=[],
        current_user_message="",
        assistant_response="",
        
        # Informations personnelles
        full_name=None,
        phone=None,
        email=None,
        
        # Critères de recherche
        transaction_type=None,
        property_type=None,
        cities=[],
        neighborhoods=[],
        budget_min=None,
        budget_max=None,
        bedrooms=None,
        surface_min=None,
        amenities=[],
        
        # Contexte
        timeframe=None,
        motivation=None,
        
        # Qualification
        budget_defined=False,
        location_defined=False,
        property_type_defined=False,
        timeframe_defined=False,
        contact_info_complete=False,
        specific_criteria_count=0,
        engagement_level=0,
        qualification_score=0,
        lead_quality="cold",
        
        # Propriétés
        matched_properties=[],
        properties_shown=False,
        
        # Contrôle
        conversation_complete=False,
        should_create_lead=False,
        lead_id=None,
        
        # Notes
        conversation_notes="",
        conversation_summary=""
    )


def update_state_with_criteria(
    state: ConversationState,
    criteria: Dict[str, Any]
) -> ConversationState:
    """
    Met à jour l'état avec de nouveaux critères extraits.
    
    Args:
        state: État actuel
        criteria: Critères extraits
        
    Returns:
        État mis à jour
    """
    # Mise à jour des critères
    if criteria.get("transaction_type"):
        state["transaction_type"] = criteria["transaction_type"]
    
    if criteria.get("property_type"):
        state["property_type"] = criteria["property_type"]
    
    if criteria.get("cities"):
        state["cities"] = list(set(state["cities"] + criteria["cities"]))
    
    if criteria.get("neighborhoods"):
        state["neighborhoods"] = list(set(state["neighborhoods"] + criteria["neighborhoods"]))
    
    if criteria.get("budget_min"):
        state["budget_min"] = criteria["budget_min"]
    
    if criteria.get("budget_max"):
        state["budget_max"] = criteria["budget_max"]
    
    if criteria.get("bedrooms"):
        state["bedrooms"] = criteria["bedrooms"]
    
    if criteria.get("surface_min"):
        state["surface_min"] = criteria["surface_min"]
    
    if criteria.get("amenities"):
        state["amenities"] = list(set(state["amenities"] + criteria["amenities"]))
    
    # Mise à jour des flags de qualification
    state["budget_defined"] = bool(state["budget_min"] or state["budget_max"])
    state["location_defined"] = bool(state["cities"] or state["neighborhoods"])
    state["property_type_defined"] = bool(state["property_type"])
    
    # Comptage des critères spécifiques
    criteria_count = 0
    if state["bedrooms"]:
        criteria_count += 1
    if state["surface_min"]:
        criteria_count += 1
    if state["amenities"]:
        criteria_count += len(state["amenities"])
    
    state["specific_criteria_count"] = criteria_count
    
    logger.debug(f"État mis à jour avec critères: {criteria}")
    return state


def is_ready_for_property_search(state: ConversationState) -> bool:
    """
    Vérifie si on a assez d'informations pour rechercher des propriétés.
    
    Args:
        state: État actuel
        
    Returns:
        True si recherche possible
    """
    # Critères minimums : budget OU localisation + type de bien
    has_budget = state["budget_defined"]
    has_location = state["location_defined"]
    has_property_type = state["property_type_defined"]
    
    # On peut chercher si on a au moins 2 critères sur 3
    criteria_count = sum([has_budget, has_location, has_property_type])
    
    ready = criteria_count >= 2
    logger.debug(f"Prêt pour recherche ? {ready} (budget:{has_budget}, loc:{has_location}, type:{has_property_type})")
    
    return ready


def is_lead_qualified(state: ConversationState) -> bool:
    """
    Vérifie si le lead est suffisamment qualifié pour être créé.
    
    Args:
        state: État actuel
        
    Returns:
        True si lead qualifié (score >= 50)
    """
    return state["qualification_score"] >= 50