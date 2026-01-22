"""
Outils pour l'agent de qualification des leads.
Fournit des fonctions pour rechercher des propriétés et calculer les scores.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PropertySearchCriteria(BaseModel):
    """Critères de recherche de propriétés."""
    
    transaction_type: Optional[str] = Field(None, description="Type de transaction: vente, location, location_vacances")
    property_type: Optional[str] = Field(None, description="Type de bien: appartement, villa, maison, riad, terrain, bureau, local_commercial")
    city: Optional[str] = Field(None, description="Ville: Casablanca, Rabat, Marrakech, etc.")
    neighborhood: Optional[str] = Field(None, description="Quartier/Secteur")
    min_price: Optional[float] = Field(None, description="Prix minimum en MAD")
    max_price: Optional[float] = Field(None, description="Prix maximum en MAD")
    min_bedrooms: Optional[int] = Field(None, description="Nombre minimum de chambres")
    min_surface: Optional[float] = Field(None, description="Surface minimum en m²")


class PropertySearchTool:
    """
    Outil de recherche de propriétés dans la base de données.
    Utilisé par l'agent IA pour matcher les critères du prospect.
    """
    
    def __init__(self, supabase_client):
        """
        Initialise l'outil de recherche.
        
        Args:
            supabase_client: Client Supabase pour accéder à la base de données
        """
        self.supabase = supabase_client
        logger.info("PropertySearchTool initialisé")
    
    async def search(
        self,
        criteria: PropertySearchCriteria,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche des propriétés selon les critères.
        
        Args:
            criteria: Critères de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de propriétés correspondantes
        """
        try:
            logger.info(f"Recherche avec critères: {criteria.model_dump(exclude_none=True)}")
            
            # Construction de la requête Supabase
            query = self.supabase.table("properties").select("*")
            
            # Filtres de base
            if criteria.transaction_type:
                query = query.eq("transaction_type", criteria.transaction_type)
            
            if criteria.property_type:
                query = query.eq("property_type", criteria.property_type)
            
            if criteria.city:
                query = query.ilike("city", f"%{criteria.city}%")
            
            if criteria.neighborhood:
                query = query.ilike("neighborhood", f"%{criteria.neighborhood}%")
            
            # Filtres sur le prix
            if criteria.min_price:
                query = query.gte("price", criteria.min_price)
            
            if criteria.max_price:
                query = query.lte("price", criteria.max_price)
            
            # Filtres sur les caractéristiques
            if criteria.min_bedrooms:
                query = query.gte("bedrooms", criteria.min_bedrooms)
            
            if criteria.min_surface:
                query = query.gte("surface", criteria.min_surface)
            
            # Exécution de la requête
            response = query.eq("status", "available").limit(limit).execute()
            
            properties = response.data if response.data else []
            logger.info(f"Trouvé {len(properties)} propriétés correspondantes")
            
            return properties
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de propriétés: {str(e)}")
            return []
    
    def format_results(self, properties: List[Dict[str, Any]]) -> str:
        """
        Formate les résultats de recherche en texte lisible.
        
        Args:
            properties: Liste de propriétés
            
        Returns:
            Texte formaté avec les résultats
        """
        if not properties:
            return "Aucune propriété ne correspond exactement à vos critères pour le moment."
        
        result = f"J'ai trouvé {len(properties)} propriété(s) intéressante(s) :\n\n"
        
        for i, prop in enumerate(properties, 1):
            result += f"{i}. {prop.get('title', 'Sans titre')}\n"
            result += f"   📍 {prop.get('city', 'N/A')}"
            if prop.get('neighborhood'):
                result += f" - {prop['neighborhood']}"
            result += f"\n"
            result += f"   💰 {prop.get('price', 0):,.0f} MAD\n"
            result += f"   🏠 {prop.get('property_type', 'N/A')} - {prop.get('surface', 0)} m²\n"
            if prop.get('bedrooms'):
                result += f"   🛏️  {prop['bedrooms']} chambres\n"
            result += "\n"
        
        return result


def calculate_qualification_score(
    budget_defined: bool = False,
    location_defined: bool = False,
    property_type_defined: bool = False,
    timeframe_defined: bool = False,
    contact_info_complete: bool = False,
    specific_criteria_count: int = 0,
    engagement_level: int = 0  # 0-10
) -> int:
    """
    Calcule le score de qualification d'un lead (0-100).
    
    Critères de scoring :
    - Budget défini: 25 points
    - Localisation définie: 20 points
    - Type de bien défini: 15 points
    - Délai de projet défini: 10 points
    - Informations de contact complètes: 15 points
    - Critères spécifiques (surface, chambres, etc.): 5 points par critère (max 10 points)
    - Niveau d'engagement (conversation): 5 points
    
    Args:
        budget_defined: Le budget est défini
        location_defined: La localisation est définie
        property_type_defined: Le type de bien est défini
        timeframe_defined: Le délai de projet est défini
        contact_info_complete: Les infos de contact sont complètes (nom, tel, email)
        specific_criteria_count: Nombre de critères spécifiques fournis
        engagement_level: Niveau d'engagement dans la conversation (0-10)
        
    Returns:
        Score de qualification entre 0 et 100
    """
    score = 0
    
    # Critères essentiels
    if budget_defined:
        score += 25
        logger.debug("Budget défini: +25 points")
    
    if location_defined:
        score += 20
        logger.debug("Localisation définie: +20 points")
    
    if property_type_defined:
        score += 15
        logger.debug("Type de bien défini: +15 points")
    
    if timeframe_defined:
        score += 10
        logger.debug("Délai défini: +10 points")
    
    if contact_info_complete:
        score += 15
        logger.debug("Contact complet: +15 points")
    
    # Critères spécifiques (max 10 points)
    criteria_points = min(specific_criteria_count * 5, 10)
    score += criteria_points
    logger.debug(f"Critères spécifiques ({specific_criteria_count}): +{criteria_points} points")
    
    # Engagement (max 5 points)
    engagement_points = min(int(engagement_level / 2), 5)
    score += engagement_points
    logger.debug(f"Engagement ({engagement_level}/10): +{engagement_points} points")
    
    logger.info(f"Score de qualification calculé: {score}/100")
    return score


def classify_lead_quality(score: int) -> str:
    """
    Classifie la qualité d'un lead selon son score.
    
    Args:
        score: Score de qualification (0-100)
        
    Returns:
        Niveau de qualité: hot, warm, cold
    """
    if score >= 70:
        return "hot"  # Lead chaud (prêt à concrétiser)
    elif score >= 50:
        return "warm"  # Lead tiède (intéressé mais besoin de maturation)
    else:
        return "cold"  # Lead froid (pas encore qualifié)


def extract_criteria_from_conversation(
    conversation_messages: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Extrait les critères mentionnés dans une conversation.
    Analyse les messages pour identifier budget, localisation, etc.
    
    Args:
        conversation_messages: Liste de messages {role: "user"|"assistant", content: "..."}
        
    Returns:
        Dictionnaire avec les critères extraits
    """
    criteria = {
        "budget_min": None,
        "budget_max": None,
        "cities": [],
        "neighborhoods": [],
        "property_types": [],
        "transaction_types": [],
        "bedrooms": None,
        "surface_min": None,
        "amenities": [],
        "timeframe": None
    }
    
    # Mots-clés pour la détection
    cities_morocco = ["casablanca", "rabat", "marrakech", "tanger", "fès", "agadir", "meknès", "oujda", "kenitra", "tétouan", "salé"]
    property_types = ["appartement", "villa", "maison", "riad", "terrain", "bureau", "local commercial"]
    transaction_types = ["vente", "location", "location vacances", "achat", "louer", "acheter"]
    
    # Analyse simple (peut être améliorée avec du NLP)
    full_text = " ".join([msg["content"].lower() for msg in conversation_messages if msg["role"] == "user"])
    
    # Détection des villes
    for city in cities_morocco:
        if city in full_text:
            criteria["cities"].append(city.capitalize())
    
    # Détection des types de bien
    for prop_type in property_types:
        if prop_type in full_text:
            criteria["property_types"].append(prop_type)
    
    # Détection du type de transaction
    for trans_type in transaction_types:
        if trans_type in full_text:
            if trans_type in ["vente", "achat", "acheter"]:
                criteria["transaction_types"].append("vente")
            elif trans_type in ["location", "louer"]:
                criteria["transaction_types"].append("location")
            elif "vacances" in trans_type:
                criteria["transaction_types"].append("location_vacances")
    
    logger.debug(f"Critères extraits: {criteria}")
    return criteria