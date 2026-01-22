# app/crud/ai_conversation.py
"""
CRUD spécialisé pour les conversations de l'Agent IA.
Gère la persistance des conversations, messages et création de leads.
"""
from typing import Optional, Dict, Any, List
from supabase import Client
from datetime import datetime
import logging
import json

from app.models import (
    Lead, LeadCreate,
    ConversationStatus
)

logger = logging.getLogger(__name__)


class AIConversationCRUD:
    """
    CRUD optimisé pour l'agent IA de qualification.
    Gère les conversations, messages et création de leads.
    """
    
    def __init__(self, db: Client):
        self.db = db
        self.conversations_table = "conversations"
        self.messages_table = "messages"
        self.leads_table = "leads"
    
    def create_conversation(
        self,
        session_id: str,
        prospect_name: Optional[str] = None,
        prospect_phone: Optional[str] = None,
        prospect_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle conversation pour l'agent IA.
        
        Args:
            session_id: ID unique de session
            prospect_name: Nom du prospect (optionnel)
            prospect_phone: Téléphone (optionnel)
            prospect_email: Email (optionnel)
            
        Returns:
            Conversation créée
        """
        try:
            data = {
                "session_id": session_id,
                "status": "active",
                "prospect_name": prospect_name,
                "prospect_phone": prospect_phone,
                "prospect_email": prospect_email,
                "message_count": 0,
                "qualification_score": 0,
                "extracted_criteria": {}
            }
            
            response = self.db.table(self.conversations_table)\
                .insert(data)\
                .execute()
            
            if not response.data:
                raise Exception("Erreur création conversation")
            
            conversation = response.data[0]
            logger.info(f"Conversation AI créée: {conversation['id']}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"Erreur création conversation AI: {e}")
            raise
    
    def get_conversation_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation par son session_id.
        
        Args:
            session_id: ID de session
            
        Returns:
            Conversation ou None
        """
        try:
            response = self.db.table(self.conversations_table)\
                .select("*")\
                .eq("session_id", session_id)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération conversation: {e}")
            return None
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation par son ID.
        
        Args:
            conversation_id: UUID de la conversation
            
        Returns:
            Conversation ou None
        """
        try:
            response = self.db.table(self.conversations_table)\
                .select("*")\
                .eq("id", conversation_id)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération conversation: {e}")
            return None
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ajoute un message à une conversation.
        
        Args:
            conversation_id: UUID de la conversation
            role: "user" ou "assistant"
            content: Contenu du message
            metadata: Métadonnées optionnelles
            
        Returns:
            Message créé
        """
        try:
            data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {}
            }
            
            response = self.db.table(self.messages_table)\
                .insert(data)\
                .execute()
            
            if not response.data:
                raise Exception("Erreur ajout message")
            
            # Incrémenter le compteur de messages
            self.db.table(self.conversations_table)\
                .update({"message_count": self.db.raw("message_count + 1")})\
                .eq("id", conversation_id)\
                .execute()
            
            logger.debug(f"Message {role} ajouté à conversation {conversation_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Erreur ajout message: {e}")
            raise
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les messages d'une conversation.
        
        Args:
            conversation_id: UUID de la conversation
            
        Returns:
            Liste des messages triés par date
        """
        try:
            response = self.db.table(self.messages_table)\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur récupération messages: {e}")
            return []
    
    def update_conversation(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Met à jour une conversation.
        
        Args:
            conversation_id: UUID de la conversation
            updates: Dictionnaire avec les champs à mettre à jour
            
        Returns:
            Conversation mise à jour
        """
        try:
            response = self.db.table(self.conversations_table)\
                .update(updates)\
                .eq("id", conversation_id)\
                .execute()
            
            if not response.data:
                raise Exception(f"Conversation {conversation_id} introuvable")
            
            logger.info(f"Conversation {conversation_id} mise à jour")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Erreur mise à jour conversation: {e}")
            raise
    
    def update_qualification_data(
        self,
        conversation_id: str,
        score: int,
        extracted_criteria: Dict[str, Any],
        lead_quality: str
    ) -> Dict[str, Any]:
        """
        Met à jour les données de qualification d'une conversation.
        
        Args:
            conversation_id: UUID de la conversation
            score: Score de qualification (0-100)
            extracted_criteria: Critères extraits
            lead_quality: Qualité (hot/warm/cold)
            
        Returns:
            Conversation mise à jour
        """
        updates = {
            "qualification_score": score,
            "extracted_criteria": extracted_criteria
        }
        
        return self.update_conversation(conversation_id, updates)
    
    def finalize_conversation(
        self,
        conversation_id: str,
        summary: str,
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Finalise une conversation (marque comme terminée).
        
        Args:
            conversation_id: UUID de la conversation
            summary: Résumé de la conversation
            lead_id: ID du lead créé (optionnel)
            
        Returns:
            Conversation finalisée
        """
        updates = {
            "status": "completed",
            "ai_qualification_summary": summary
        }
        
        if lead_id:
            updates["lead_id"] = lead_id
        
        return self.update_conversation(conversation_id, updates)
    
    def create_lead_from_conversation(
        self,
        conversation_id: str,
        state: Dict[str, Any]
    ) -> str:
        """
        Crée un lead à partir d'une conversation qualifiée.
        
        Args:
            conversation_id: UUID de la conversation
            state: État de la conversation (ConversationState)
            
        Returns:
            ID du lead créé
        """
        try:
            # Préparation des données du lead
            lead_data = {
                "first_name": (state.get("full_name") or "Prospect").split()[0],
                "last_name": " ".join((state.get("full_name") or "Prospect").split()[1:]) or "IA",
                "phone": state.get("phone") or "Non fourni",
                "email": state.get("email"),
                "source": "chatbot",
                "status": "new",
                "priority": "high" if state.get("lead_quality") == "hot" else "medium",
                
                # Critères de recherche
                "transaction_type": state.get("transaction_type"),
                "property_types": state.get("property_type"),
                "budget_min": state.get("budget_min"),
                "budget_max": state.get("budget_max"),
                "preferred_cities": state.get("cities", []),
                "preferred_districts": state.get("neighborhoods", []),
                "min_bedrooms": state.get("bedrooms"),
                "min_area": state.get("surface_min"),
                
                # Équipements
                "must_have_parking": "parking" in state.get("amenities", []),
                "must_have_garden": "jardin" in state.get("amenities", []),
                "must_have_pool": "piscine" in state.get("amenities", []),
                "must_have_elevator": "ascenseur" in state.get("amenities", []),
                
                # Qualification
                "qualification_score": state.get("qualification_score", 0),
                "matched_properties": [p.get("id") for p in state.get("matched_properties", []) if p.get("id")],
                
                # Notes
                "notes": f"Lead qualifié par Agent IA - Score: {state.get('qualification_score')}/100\n" +
                         f"Délai: {state.get('timeframe') or 'Non spécifié'}\n" +
                         f"Motivation: {state.get('motivation') or 'Non spécifié'}",
                "ai_conversation_summary": state.get("conversation_summary", ""),
                "conversation_id": conversation_id
            }
            
            # Insertion dans la base
            response = self.db.table(self.leads_table)\
                .insert(lead_data)\
                .execute()
            
            if not response.data:
                raise Exception("Erreur création lead")
            
            lead_id = response.data[0]["id"]
            logger.info(f"Lead créé automatiquement: {lead_id}")
            
            # Mettre à jour la conversation avec le lead_id
            self.update_conversation(conversation_id, {"lead_id": lead_id})
            
            return lead_id
            
        except Exception as e:
            logger.error(f"Erreur création lead depuis conversation: {e}")
            raise
    
    def get_conversation_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur les conversations IA.
        
        Returns:
            Dictionnaire avec statistiques
        """
        try:
            # Total conversations
            total_response = self.db.table(self.conversations_table)\
                .select("id", count="exact")\
                .execute()
            
            # Conversations actives
            active_response = self.db.table(self.conversations_table)\
                .select("id", count="exact")\
                .eq("status", "active")\
                .execute()
            
            # Conversations terminées
            completed_response = self.db.table(self.conversations_table)\
                .select("id", count="exact")\
                .eq("status", "completed")\
                .execute()
            
            # Leads créés
            with_leads_response = self.db.table(self.conversations_table)\
                .select("id", count="exact")\
                .not_.is_("lead_id", "null")\
                .execute()
            
            return {
                "total_conversations": total_response.count or 0,
                "active_conversations": active_response.count or 0,
                "completed_conversations": completed_response.count or 0,
                "leads_created": with_leads_response.count or 0,
                "conversion_rate": (
                    (with_leads_response.count or 0) / (completed_response.count or 1) * 100
                ) if completed_response.count else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            return {
                "total_conversations": 0,
                "active_conversations": 0,
                "completed_conversations": 0,
                "leads_created": 0,
                "conversion_rate": 0
            }


def get_ai_conversation_crud(db: Client) -> AIConversationCRUD:
    """Factory function pour créer une instance AIConversationCRUD."""
    return AIConversationCRUD(db)
