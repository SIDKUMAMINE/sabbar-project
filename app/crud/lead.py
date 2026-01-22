# app/crud/lead.py
"""
Opérations CRUD pour les leads (prospects)
"""

from typing import Optional, List, Dict, Any
from supabase import Client
from datetime import datetime
import logging

from app.models import (
    Lead, LeadCreate, LeadUpdate, LeadList,
    LeadStatus, LeadSource, LeadPriority
)

logger = logging.getLogger(__name__)


class LeadCRUD:
    """Classe pour gérer les opérations CRUD sur les leads"""
    
    def __init__(self, db: Client):
        self.db = db
        self.table_name = "leads"
    
    def create(self, lead_data: LeadCreate) -> Lead:
        """
        Créer un nouveau lead
        
        Args:
            lead_data: Données du lead à créer
            
        Returns:
            Lead créé avec son ID
            
        Raises:
            Exception: Si la création échoue
        """
        try:
            # Convertir les données Pydantic en dict
            data = lead_data.model_dump()
            
            # Convertir les listes Python en JSON pour Supabase
            if data.get('preferred_cities'):
                data['preferred_cities'] = data['preferred_cities']
            if data.get('preferred_districts'):
                data['preferred_districts'] = data['preferred_districts']
            if data.get('property_types'):
                data['property_types'] = data['property_types']
            if data.get('matched_properties'):
                data['matched_properties'] = data['matched_properties']
            
            # Insérer dans Supabase
            response = self.db.table(self.table_name).insert(data).execute()
            
            if not response.data:
                raise Exception("Aucune donnée retournée après insertion")
            
            logger.info(f"Lead créé avec succès: {response.data[0]['id']}")
            return Lead(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur création lead: {e}")
            raise
    
    def get_by_id(self, lead_id: str) -> Optional[Lead]:
        """
        Récupérer un lead par son ID
        
        Args:
            lead_id: UUID du lead
            
        Returns:
            Lead trouvé ou None
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("id", lead_id)\
                .execute()
            
            if response.data:
                return Lead(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération lead {lead_id}: {e}")
            raise
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[LeadStatus] = None,
        source: Optional[LeadSource] = None,
        priority: Optional[LeadPriority] = None,
        min_score: Optional[int] = None,
        assigned_to: Optional[str] = None
    ) -> List[LeadList]:
        """
        Récupérer tous les leads avec filtres optionnels
        
        Args:
            skip: Nombre d'éléments à sauter (pagination)
            limit: Nombre maximum d'éléments à retourner
            status: Filtrer par statut
            source: Filtrer par source
            priority: Filtrer par priorité
            min_score: Score minimum de qualification
            assigned_to: Filtrer par agent assigné
            
        Returns:
            Liste des leads
        """
        try:
            query = self.db.table(self.table_name).select("*")
            
            # Appliquer les filtres
            if status:
                query = query.eq("status", status.value)
            if source:
                query = query.eq("source", source.value)
            if priority:
                query = query.eq("priority", priority.value)
            if min_score is not None:
                query = query.gte("qualification_score", min_score)
            if assigned_to:
                query = query.eq("assigned_to", assigned_to)
            
            # Pagination et tri
            query = query.order("created_at", desc=True)
            query = query.range(skip, skip + limit - 1)
            
            response = query.execute()
            
            return [LeadList(**lead) for lead in response.data]
            
        except Exception as e:
            logger.error(f"Erreur récupération liste leads: {e}")
            raise
    
    def update(self, lead_id: str, lead_data: LeadUpdate) -> Lead:
        """
        Mettre à jour un lead
        
        Args:
            lead_id: UUID du lead
            lead_data: Données à mettre à jour
            
        Returns:
            Lead mis à jour
            
        Raises:
            Exception: Si la mise à jour échoue
        """
        try:
            # Convertir en dict en excluant les valeurs None
            update_dict = lead_data.model_dump(exclude_unset=True)
            
            if not update_dict:
                raise ValueError("Aucune donnée à mettre à jour")
            
            # Mettre à jour dans Supabase
            response = self.db.table(self.table_name)\
                .update(update_dict)\
                .eq("id", lead_id)\
                .execute()
            
            if not response.data:
                raise Exception(f"Lead {lead_id} introuvable")
            
            logger.info(f"Lead {lead_id} mis à jour")
            return Lead(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur mise à jour lead {lead_id}: {e}")
            raise
    
    def delete(self, lead_id: str) -> bool:
        """
        Supprimer un lead
        
        Args:
            lead_id: UUID du lead
            
        Returns:
            True si supprimé
        """
        try:
            response = self.db.table(self.table_name)\
                .delete()\
                .eq("id", lead_id)\
                .execute()
            
            logger.info(f"Lead {lead_id} supprimé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression lead {lead_id}: {e}")
            raise
    
    def update_status(self, lead_id: str, new_status: LeadStatus) -> Lead:
        """
        Mettre à jour uniquement le statut d'un lead
        
        Args:
            lead_id: UUID du lead
            new_status: Nouveau statut
            
        Returns:
            Lead mis à jour
        """
        update_data = LeadUpdate(status=new_status)
        return self.update(lead_id, update_data)
    
    def mark_contacted(self, lead_id: str) -> Lead:
        """
        Marquer un lead comme contacté
        
        Args:
            lead_id: UUID du lead
            
        Returns:
            Lead mis à jour
        """
        try:
            response = self.db.table(self.table_name)\
                .update({
                    "status": "contacted",
                    "last_contacted_at": datetime.utcnow().isoformat()
                })\
                .eq("id", lead_id)\
                .execute()
            
            if not response.data:
                raise Exception(f"Lead {lead_id} introuvable")
            
            logger.info(f"Lead {lead_id} marqué comme contacté")
            return Lead(**response.data[0])
            
        except Exception as e:
            logger.error(f"Erreur mark_contacted {lead_id}: {e}")
            raise
    
    def get_by_phone(self, phone: str) -> Optional[Lead]:
        """
        Rechercher un lead par numéro de téléphone
        
        Args:
            phone: Numéro de téléphone
            
        Returns:
            Lead trouvé ou None
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("phone", phone)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                return Lead(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Erreur recherche lead par téléphone: {e}")
            raise
    
    def get_high_priority_leads(self, limit: int = 10) -> List[LeadList]:
        """
        Récupérer les leads à haute priorité non traités
        
        Args:
            limit: Nombre maximum de leads
            
        Returns:
            Liste des leads prioritaires
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .in_("status", ["new", "contacted"])\
                .in_("priority", ["high", "urgent"])\
                .order("priority", desc=True)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [LeadList(**lead) for lead in response.data]
            
        except Exception as e:
            logger.error(f"Erreur récupération leads prioritaires: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupérer des statistiques sur les leads
        
        Returns:
            Dictionnaire avec les stats
        """
        try:
            # Compter tous les leads
            total = self.db.table(self.table_name)\
                .select("id", count="exact")\
                .execute()
            
            # Par statut
            by_status = {}
            for status in LeadStatus:
                count = self.db.table(self.table_name)\
                    .select("id", count="exact")\
                    .eq("status", status.value)\
                    .execute()
                by_status[status.value] = count.count or 0
            
            # Score moyen
            avg_score = self.db.table(self.table_name)\
                .select("qualification_score")\
                .execute()
            
            scores = [lead['qualification_score'] for lead in avg_score.data if lead.get('qualification_score')]
            avg = sum(scores) / len(scores) if scores else 0
            
            return {
                "total_leads": total.count or 0,
                "by_status": by_status,
                "average_qualification_score": round(avg, 2),
                "high_priority_count": by_status.get("high", 0) + by_status.get("urgent", 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            raise


def get_lead_crud(db: Client) -> LeadCRUD:
    """Factory function pour créer une instance LeadCRUD"""
    return LeadCRUD(db)