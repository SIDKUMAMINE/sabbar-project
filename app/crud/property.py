"""
Opérations CRUD pour Properties
"""
from typing import List, Optional
from supabase import Client
from app.models import PropertyCreate, PropertyUpdate, Property, PropertyList
import logging

logger = logging.getLogger(__name__)

class PropertyCRUD:
    def __init__(self, db: Client):
        self.db = db
        self.table = "properties"
    
    def create(self, property_data: PropertyCreate, agent_id: Optional[str] = None) -> Property:
        """Créer une nouvelle annonce"""
        try:
            data = property_data.model_dump()
            if agent_id:
                data["agent_id"] = agent_id
            
            result = self.db.table(self.table).insert(data).execute()
            
            if result.data:
                logger.info(f"✓ Propriété créée: {result.data[0]['id']}")
                return Property(**result.data[0])
            else:
                raise Exception("Erreur lors de la création")
                
        except Exception as e:
            logger.error(f"✗ Erreur création propriété: {e}")
            raise
    
    def get_by_id(self, property_id: str) -> Optional[Property]:
        """Récupérer une annonce par ID"""
        try:
            result = self.db.table(self.table)\
                .select("*")\
                .eq("id", property_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return Property(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"✗ Erreur récupération propriété {property_id}: {e}")
            return None
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 20,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[PropertyList]:
        """Liste des annonces avec filtres"""
        try:
            query = self.db.table(self.table).select("*")
            
            if city:
                query = query.eq("city", city)
            if property_type:
                query = query.eq("property_type", property_type)
            if transaction_type:
                query = query.eq("transaction_type", transaction_type)
            if min_price:
                query = query.gte("price", min_price)
            if max_price:
                query = query.lte("price", max_price)
            
            result = query\
                .order("created_at", desc=True)\
                .range(skip, skip + limit - 1)\
                .execute()
            
            if result.data:
                return [PropertyList(**item) for item in result.data]
            return []
            
        except Exception as e:
            logger.error(f"✗ Erreur récupération propriétés: {e}")
            return []
    
    def update(self, property_id: str, property_data: PropertyUpdate) -> Optional[Property]:
        """Mettre à jour une annonce"""
        try:
            data = property_data.model_dump(exclude_unset=True)
            
            if not data:
                raise ValueError("Aucune donnée à mettre à jour")
            
            result = self.db.table(self.table)\
                .update(data)\
                .eq("id", property_id)\
                .execute()
            
            if result.data:
                logger.info(f"✓ Propriété mise à jour: {property_id}")
                return Property(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"✗ Erreur mise à jour propriété {property_id}: {e}")
            raise
    
    def delete(self, property_id: str) -> bool:
        """Supprimer une annonce"""
        try:
            self.db.table(self.table).delete().eq("id", property_id).execute()
            logger.info(f"✓ Propriété supprimée: {property_id}")
            return True
        except Exception as e:
            logger.error(f"✗ Erreur suppression propriété {property_id}: {e}")
            return False
    
    def increment_views(self, property_id: str) -> bool:
        """Incrémenter vues"""
        try:
            property_obj = self.get_by_id(property_id)
            if property_obj:
                new_count = property_obj.views_count + 1
                self.db.table(self.table)\
                    .update({"views_count": new_count})\
                    .eq("id", property_id)\
                    .execute()
            return True
        except:
            return False

def get_property_crud(db: Client) -> PropertyCRUD:
    return PropertyCRUD(db) 