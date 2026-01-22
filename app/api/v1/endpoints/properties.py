"""
Routes API pour les annonces immobilières
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from supabase import Client
from pydantic import ValidationError
import logging
from app.db import get_supabase
from app.crud import get_property_crud
from app.models import Property, PropertyCreate, PropertyUpdate, PropertyList

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=Property, status_code=201)
def create_property(
    property_data: PropertyCreate,
    db: Client = Depends(get_supabase)
):
    """Créer une nouvelle annonce"""
    try:
        crud = get_property_crud(db)
        return crud.create(property_data)
    except ValidationError as e:
        logger.error(f"Erreur de validation lors de la création: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'annonce: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'annonce"
        )

@router.get("/", response_model=List[PropertyList])
def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Client = Depends(get_supabase)
):
    """Liste des annonces avec filtres optionnels"""
    try:
        crud = get_property_crud(db)
        return crud.get_all(
            skip=skip, limit=limit, city=city,
            property_type=property_type,
            transaction_type=transaction_type,
            min_price=min_price, max_price=max_price
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des annonces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des annonces"
        )

@router.get("/{property_id}", response_model=Property)
def get_property(
    property_id: str,
    db: Client = Depends(get_supabase)
):
    """Récupérer une annonce par son ID"""
    try:
        crud = get_property_crud(db)
        property_obj = crud.get_by_id(property_id)
        
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Annonce {property_id} non trouvée"
            )
        
        # Incrémenter le compteur de vues
        crud.increment_views(property_id)
        return property_obj
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'annonce {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'annonce"
        )

@router.put("/{property_id}", response_model=Property)
def update_property(
    property_id: str,
    property_data: PropertyUpdate,
    db: Client = Depends(get_supabase)
):
    """Mettre à jour une annonce existante"""
    try:
        crud = get_property_crud(db)
        
        # Vérifier que l'annonce existe
        existing = crud.get_by_id(property_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Annonce {property_id} non trouvée"
            )
        
        # Vérifier qu'il y a des données à mettre à jour
        update_dict = property_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucune donnée à mettre à jour"
            )
        
        # Effectuer la mise à jour
        updated_property = crud.update(property_id, property_data)
        logger.info(f"Annonce {property_id} mise à jour avec succès")
        return updated_property
    
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Erreur de validation pour l'annonce {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'annonce {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de l'annonce"
        )

@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: str,
    db: Client = Depends(get_supabase)
):
    """Supprimer une annonce"""
    try:
        crud = get_property_crud(db)
        
        # Vérifier que l'annonce existe
        existing = crud.get_by_id(property_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Annonce {property_id} non trouvée"
            )
        
        # Supprimer l'annonce
        crud.delete(property_id)
        logger.info(f"Annonce {property_id} supprimée avec succès")
        return None  # 204 No Content
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'annonce {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'annonce"
        )