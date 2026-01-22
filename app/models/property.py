# app/models/property.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class PropertyType(str, Enum):
    apartment = "apartment"
    villa = "villa"
    house = "house"
    riad = "riad"
    land = "land"
    office = "office"
    commercial = "commercial"

class TransactionType(str, Enum):
    sale = "sale"
    rent = "rent"
    vacation_rental = "vacation_rental"

class PropertyBase(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)  # ✅ Réduit de 50 à 20
    price: float = Field(..., gt=0)
    property_type: PropertyType
    transaction_type: TransactionType
    city: str = Field(..., min_length=2, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    area: float = Field(..., gt=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = None
    has_parking: bool = False
    has_garden: bool = False
    has_pool: bool = False
    has_elevator: bool = False
    is_furnished: bool = False
    is_available: bool = True
    images: Optional[list[str]] = []

class PropertyCreate(PropertyBase):
    owner_id: str = Field(..., min_length=1)

class PropertyUpdate(BaseModel):
    """Tous les champs sont optionnels pour la mise à jour"""
    title: Optional[str] = Field(None, min_length=10, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=2000)  # ✅ Réduit
    price: Optional[float] = Field(None, gt=0)
    property_type: Optional[PropertyType] = None
    transaction_type: Optional[TransactionType] = None
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    area: Optional[float] = Field(None, gt=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = None
    has_parking: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_elevator: Optional[bool] = None
    is_furnished: Optional[bool] = None
    is_available: Optional[bool] = None
    images: Optional[list[str]] = None

class PropertyList(BaseModel):
    """Version simplifiée pour les listes"""
    id: str
    title: str
    price: float
    property_type: PropertyType
    transaction_type: TransactionType
    city: str
    district: Optional[str]
    area: float
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    images: Optional[list[str]]
    created_at: datetime

    class Config:
        from_attributes = True

class Property(PropertyBase):
    """Modèle complet avec métadonnées"""
    id: str
    owner_id: str
    views: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True