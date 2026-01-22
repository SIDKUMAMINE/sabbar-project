# app/api/v1/endpoints/leads.py
"""
Routes API pour les leads (prospects)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from supabase import Client
import logging
from app.db import get_supabase
from app.crud import get_lead_crud
from app.models import (
    Lead, LeadCreate, LeadUpdate, LeadList,
    LeadStatus, LeadSource, LeadPriority
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=Lead, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_data: LeadCreate,
    db: Client = Depends(get_supabase)
):
    """
    Créer un nouveau lead
    
    - **first_name**: Prénom (min 2 caractères)
    - **last_name**: Nom (min 2 caractères)
    - **phone**: Téléphone format marocain (+212XXXXXXXXX ou 0XXXXXXXXX)
    - **email**: Email (optionnel)
    - **budget_min/budget_max**: Fourchette de budget en MAD
    - **preferred_cities**: Liste des villes souhaitées
    - **property_types**: Types de biens recherchés (apartment, villa, etc.)
    - **qualification_score**: Score de 0 à 100
    """
    try:
        crud = get_lead_crud(db)
        lead = crud.create(lead_data)
        logger.info(f"Lead créé: {lead.id}")
        return lead
        
    except Exception as e:
        logger.error(f"Erreur création lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du lead: {str(e)}"
        )


@router.get("/", response_model=List[LeadList])
def list_leads(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum d'éléments"),
    status: Optional[LeadStatus] = Query(None, description="Filtrer par statut"),
    source: Optional[LeadSource] = Query(None, description="Filtrer par source"),
    priority: Optional[LeadPriority] = Query(None, description="Filtrer par priorité"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Score minimum"),
    assigned_to: Optional[str] = Query(None, description="Filtrer par agent assigné"),
    db: Client = Depends(get_supabase)
):
    """
    Liste des leads avec filtres optionnels
    
    Permet de filtrer par:
    - **status**: new, contacted, qualified, meeting_scheduled, etc.
    - **source**: agent_ia, web_form, phone, email, etc.
    - **priority**: low, medium, high, urgent
    - **min_score**: Score de qualification minimum
    - **assigned_to**: ID de l'agent immobilier
    """
    try:
        crud = get_lead_crud(db)
        leads = crud.get_all(
            skip=skip,
            limit=limit,
            status=status,
            source=source,
            priority=priority,
            min_score=min_score,
            assigned_to=assigned_to
        )
        return leads
        
    except Exception as e:
        logger.error(f"Erreur récupération leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des leads"
        )


@router.get("/statistics")
def get_lead_statistics(
    db: Client = Depends(get_supabase)
):
    """
    Statistiques sur les leads
    
    Retourne:
    - Nombre total de leads
    - Répartition par statut
    - Score moyen de qualification
    - Nombre de leads haute priorité
    """
    try:
        crud = get_lead_crud(db)
        stats = crud.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Erreur calcul statistiques: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du calcul des statistiques"
        )


@router.get("/high-priority", response_model=List[LeadList])
def get_high_priority_leads(
    limit: int = Query(10, ge=1, le=50),
    db: Client = Depends(get_supabase)
):
    """
    Récupérer les leads à haute priorité non traités
    
    Retourne les leads avec priority=high ou urgent et status=new ou contacted
    """
    try:
        crud = get_lead_crud(db)
        leads = crud.get_high_priority_leads(limit=limit)
        return leads
        
    except Exception as e:
        logger.error(f"Erreur récupération leads prioritaires: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des leads prioritaires"
        )


@router.get("/search/phone/{phone}", response_model=Lead)
def search_lead_by_phone(
    phone: str,
    db: Client = Depends(get_supabase)
):
    """
    Rechercher un lead par numéro de téléphone
    
    Format accepté: +212XXXXXXXXX ou 0XXXXXXXXX
    """
    try:
        crud = get_lead_crud(db)
        lead = crud.get_by_phone(phone)
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucun lead trouvé avec le téléphone {phone}"
            )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recherche lead par téléphone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la recherche"
        )


@router.get("/{lead_id}", response_model=Lead)
def get_lead(
    lead_id: str,
    db: Client = Depends(get_supabase)
):
    """
    Récupérer un lead par son ID
    """
    try:
        crud = get_lead_crud(db)
        lead = crud.get_by_id(lead_id)
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} introuvable"
            )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération lead {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du lead"
        )


@router.put("/{lead_id}", response_model=Lead)
def update_lead(
    lead_id: str,
    lead_data: LeadUpdate,
    db: Client = Depends(get_supabase)
):
    """
    Mettre à jour un lead
    
    Tous les champs sont optionnels. Seuls les champs fournis seront modifiés.
    """
    try:
        crud = get_lead_crud(db)
        
        # Vérifier que le lead existe
        existing = crud.get_by_id(lead_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} introuvable"
            )
        
        # Mettre à jour
        updated_lead = crud.update(lead_id, lead_data)
        logger.info(f"Lead {lead_id} mis à jour")
        return updated_lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour lead {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du lead"
        )


@router.patch("/{lead_id}/status", response_model=Lead)
def update_lead_status(
    lead_id: str,
    new_status: LeadStatus,
    db: Client = Depends(get_supabase)
):
    """
    Mettre à jour uniquement le statut d'un lead
    
    Statuts disponibles:
    - new: Nouveau lead
    - contacted: Lead contacté
    - qualified: Lead qualifié
    - meeting_scheduled: RDV programmé
    - proposal_sent: Proposition envoyée
    - negotiation: En négociation
    - converted: Converti en client
    - lost: Perdu
    - archived: Archivé
    """
    try:
        crud = get_lead_crud(db)
        
        # Vérifier que le lead existe
        existing = crud.get_by_id(lead_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} introuvable"
            )
        
        # Mettre à jour le statut
        updated_lead = crud.update_status(lead_id, new_status)
        logger.info(f"Statut du lead {lead_id} mis à jour: {new_status}")
        return updated_lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour statut lead {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du statut"
        )


@router.patch("/{lead_id}/mark-contacted", response_model=Lead)
def mark_lead_contacted(
    lead_id: str,
    db: Client = Depends(get_supabase)
):
    """
    Marquer un lead comme contacté
    
    Met à jour le statut à 'contacted' et enregistre la date de dernier contact
    """
    try:
        crud = get_lead_crud(db)
        
        # Vérifier que le lead existe
        existing = crud.get_by_id(lead_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} introuvable"
            )
        
        # Marquer comme contacté
        updated_lead = crud.mark_contacted(lead_id)
        logger.info(f"Lead {lead_id} marqué comme contacté")
        return updated_lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mark_contacted {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du marquage du lead"
        )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: str,
    db: Client = Depends(get_supabase)
):
    """
    Supprimer un lead
    
    ⚠️ Attention: Cette action est irréversible
    """
    try:
        crud = get_lead_crud(db)
        
        # Vérifier que le lead existe
        existing = crud.get_by_id(lead_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} introuvable"
            )
        
        # Supprimer
        crud.delete(lead_id)
        logger.info(f"Lead {lead_id} supprimé")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression lead {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression du lead"
        )