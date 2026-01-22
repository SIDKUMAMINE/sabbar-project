# app/models/user.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """Rôles utilisateurs"""
    ADMIN = "admin"
    AGENT = "agent"
    MANAGER = "manager"

class UserStatus(str, Enum):
    """Statut utilisateur"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

# Base
class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    phone: Optional[str] = Field(None, pattern=r"^(\+212|0)[5-7]\d{8}$")
    role: UserRole = UserRole.AGENT
    
    # Profil agent
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    specialties: Optional[List[str]] = Field(default_factory=list)  # Spécialités
    cities_covered: Optional[List[str]] = Field(default_factory=list)

# Création (avec mot de passe)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Mise à jour
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None

# Complet
class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: UserStatus = UserStatus.ACTIVE
    
    # Stats
    properties_count: int = 0
    leads_count: int = 0
    conversions_count: int = 0
    
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

# Réponse login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User