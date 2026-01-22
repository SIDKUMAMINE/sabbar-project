# app/crud/conversation.py
"""
Opérations CRUD pour les conversations et messages
"""

from typing import Optional, List
from supabase import Client
from datetime import datetime
import logging

from app.models import (
    Conversation, ConversationCreate, ConversationUpdate,
    ConversationList, ConversationWithMessages,
    Message, MessageAdd, MessageRole, ConversationStatus
)

logger = logging.getLogger(__name__)


class ConversationCRUD:
    """Classe pour gérer les opérations CRUD sur les conversations"""
    
    def __init__(self, db: Client):
        self.db = db
        self.conversations_table = "conversations"
        self.messages_table = "messages"
    
    def create(self, conversation_data: ConversationCreate) -> Conversation:
        """
        Créer une nouvelle conversation
        
        Args:
            conversation_data: Données de la conversation
            
        Returns:
            Conversation créée
        """
        try:
            # Préparer les données
            data = {
                "prospect_name": conversation_data.prospect_name,
                "prospect_phone": conversation_data.prospect_phone,
                "prospect_email": conversation_data.prospect_email,
                "status": "active",
                "message_count": 0
            }
            
            # Insérer dans Supabase
            response = self.db.table(self.conversations_table)\
                .insert(data)\
                .execute()
            
            if not response.data:
                raise Exception("Aucune donnée retournée")
            
            conversation_id = response.data[0]['id']
            
            # Ajouter le message initial si fourni
            if conversation_data.initial_message:
                self.add_message(
                    conversation_id,
                    MessageAdd(content=conversation_data.initial_message)
                )
            
            logger.info(f"Conversation créée: {conversation_id}")
            return Conversation(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur création conversation: {e}")
            raise
    
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Récupérer une conversation par ID"""
        try:
            response = self.db.table(self.conversations_table)\
                .select("*")\
                .eq("id", conversation_id)\
                .execute()
            
            if response.data:
                return Conversation(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération conversation {conversation_id}: {e}")
            raise
    
    def get_with_messages(self, conversation_id: str) -> Optional[ConversationWithMessages]:
        """
        Récupérer une conversation avec tous ses messages
        
        Args:
            conversation_id: UUID de la conversation
            
        Returns:
            Conversation avec messages ou None
        """
        try:
            # Récupérer la conversation
            conversation = self.get_by_id(conversation_id)
            if not conversation:
                return None
            
            # Récupérer les messages
            messages = self.get_messages(conversation_id)
            
            # Construire l'objet complet
            conv_dict = conversation.model_dump()
            conv_dict['messages'] = messages
            
            return ConversationWithMessages(**conv_dict)
            
        except Exception as e:
            logger.error(f"Erreur récupération conversation avec messages: {e}")
            raise
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ConversationStatus] = None
    ) -> List[ConversationList]:
        """Récupérer toutes les conversations"""
        try:
            query = self.db.table(self.conversations_table).select("*")
            
            if status:
                query = query.eq("status", status.value)
            
            query = query.order("created_at", desc=True)
            query = query.range(skip, skip + limit - 1)
            
            response = query.execute()
            
            return [ConversationList(**conv) for conv in response.data]
            
        except Exception as e:
            logger.error(f"Erreur récupération conversations: {e}")
            raise
    
    def update(self, conversation_id: str, conversation_data: ConversationUpdate) -> Conversation:
        """Mettre à jour une conversation"""
        try:
            update_dict = conversation_data.model_dump(exclude_unset=True)
            
            if not update_dict:
                raise ValueError("Aucune donnée à mettre à jour")
            
            response = self.db.table(self.conversations_table)\
                .update(update_dict)\
                .eq("id", conversation_id)\
                .execute()
            
            if not response.data:
                raise Exception(f"Conversation {conversation_id} introuvable")
            
            logger.info(f"Conversation {conversation_id} mise à jour")
            return Conversation(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur mise à jour conversation {conversation_id}: {e}")
            raise
    
    def delete(self, conversation_id: str) -> bool:
        """Supprimer une conversation (et ses messages en cascade)"""
        try:
            self.db.table(self.conversations_table)\
                .delete()\
                .eq("id", conversation_id)\
                .execute()
            
            logger.info(f"Conversation {conversation_id} supprimée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression conversation {conversation_id}: {e}")
            raise
    
    # ========================================
    # Gestion des messages
    # ========================================
    
    def add_message(
        self,
        conversation_id: str,
        message_data: MessageAdd,
        role: MessageRole = MessageRole.user
    ) -> Message:
        """
        Ajouter un message à une conversation
        
        Args:
            conversation_id: UUID de la conversation
            message_data: Contenu du message
            role: Rôle (user, assistant, system)
            
        Returns:
            Message créé
        """
        try:
            data = {
                "conversation_id": conversation_id,
                "role": role.value,
                "content": message_data.content,
                "metadata": message_data.metadata or {}
            }
            
            response = self.db.table(self.messages_table)\
                .insert(data)\
                .execute()
            
            if not response.data:
                raise Exception("Erreur insertion message")
            
            logger.info(f"Message ajouté à conversation {conversation_id}")
            return Message(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur ajout message: {e}")
            raise
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Récupérer les messages d'une conversation
        
        Args:
            conversation_id: UUID de la conversation
            limit: Nombre maximum de messages (None = tous)
            
        Returns:
            Liste des messages triés par date
        """
        try:
            query = self.db.table(self.messages_table)\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            return [Message(**msg) for msg in response.data]
            
        except Exception as e:
            logger.error(f"Erreur récupération messages: {e}")
            raise
    
    def complete_conversation(
        self,
        conversation_id: str,
        lead_id: Optional[str] = None
    ) -> Conversation:
        """
        Marquer une conversation comme terminée
        
        Args:
            conversation_id: UUID de la conversation
            lead_id: UUID du lead créé (optionnel)
            
        Returns:
            Conversation mise à jour
        """
        try:
            # Calculer la durée
            conversation = self.get_by_id(conversation_id)
            if not conversation:
                raise Exception(f"Conversation {conversation_id} introuvable")
            
            duration = int((datetime.utcnow() - conversation.created_at).total_seconds())
            
            # Mettre à jour
            update_data = {
                "status": "completed",
                "duration_seconds": duration
            }
            
            if lead_id:
                update_data["lead_id"] = lead_id
            
            response = self.db.table(self.conversations_table)\
                .update(update_data)\
                .eq("id", conversation_id)\
                .execute()
            
            logger.info(f"Conversation {conversation_id} terminée")
            return Conversation(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur completion conversation: {e}")
            raise
    
    def get_active_conversations(self, limit: int = 20) -> List[ConversationList]:
        """Récupérer les conversations actives"""
        return self.get_all(limit=limit, status=ConversationStatus.active)


def get_conversation_crud(db: Client) -> ConversationCRUD:
    """Factory function pour créer une instance ConversationCRUD"""
    return ConversationCRUD(db)