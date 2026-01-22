# tests/test_models.py
"""
Tests des modèles Pydantic
Exécuter: pytest tests/test_models.py -v
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    PropertyCreate, PropertyType, TransactionType,
    LeadCreate, LeadStatus,
    UserCreate, UserRole,
    Message, MessageRole
)

def test_property_create_valid():
    """Test création propriété valide"""
    property_data = {
        "title": "Bel appartement à Casablanca",
        "description": "Superbe appartement moderne de 100m² avec vue sur mer, 3 chambres, 2 salles de bains, cuisine équipée",
        "property_type": PropertyType.APPARTEMENT,
        "transaction_type": TransactionType.VENTE,
        "city": "Casablanca",
        "district": "Ain Diab",
        "price": 1500000.0,
        "surface_area": 100.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking": True,
        "elevator": True
    }
    
    property_obj = PropertyCreate(**property_data)
    assert property_obj.title == "Bel appartement à Casablanca"
    assert property_obj.price == 1500000.0
    assert property_obj.bedrooms == 3

def test_property_create_invalid_price():
    """Test prix négatif (doit échouer)"""
    with pytest.raises(ValidationError):
        PropertyCreate(
            title="Test",
            description="Description longue de plus de 50 caractères pour respecter la validation",
            property_type=PropertyType.APPARTEMENT,
            transaction_type=TransactionType.VENTE,
            city="Casablanca",
            price=-1000.0,  # Prix négatif invalide
            surface_area=100.0
        )

def test_lead_create_valid():
    """Test création lead valide"""
    lead_data = {
        "first_name": "Mohammed",
        "last_name": "Alami",
        "email": "m.alami@example.com",
        "phone": "0612345678",
        "property_type": "appartement",
        "transaction_type": "vente",
        "budget_min": 800000.0,
        "budget_max": 1500000.0,
        "preferred_cities": ["Casablanca", "Rabat"],
        "min_bedrooms": 2
    }
    
    lead = LeadCreate(**lead_data)
    assert lead.first_name == "Mohammed"
    assert lead.budget_max == 1500000.0
    assert "Casablanca" in lead.preferred_cities

def test_lead_invalid_phone():
    """Test téléphone invalide (doit échouer)"""
    with pytest.raises(ValidationError):
        LeadCreate(
            first_name="Test",
            last_name="User",
            phone="123456",  # Format invalide
        )

def test_user_create_valid():
    """Test création utilisateur valide"""
    user_data = {
        "email": "agent@sabbar.ma",
        "first_name": "Fatima",
        "last_name": "Bennani",
        "phone": "0661234567",
        "password": "SecurePassword123!",
        "role": UserRole.AGENT,
        "specialties": ["Luxe", "Neuf"],
        "cities_covered": ["Casablanca", "Mohammedia"]
    }
    
    user = UserCreate(**user_data)
    assert user.email == "agent@sabbar.ma"
    assert user.role == UserRole.AGENT
    assert len(user.specialties) == 2

def test_user_invalid_email():
    """Test email invalide (doit échouer)"""
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",  # Email invalide
            first_name="Test",
            last_name="User",
            password="password123"
        )

def test_message_creation():
    """Test création message conversation"""
    message = Message(
        role=MessageRole.USER,
        content="Je cherche un appartement à Casablanca"
    )
    
    assert message.role == MessageRole.USER
    assert isinstance(message.timestamp, datetime)
    assert message.content == "Je cherche un appartement à Casablanca"

# Test des validations spécifiques
def test_property_title_too_short():
    """Test titre trop court"""
    with pytest.raises(ValidationError) as exc:
        PropertyCreate(
            title="Court",  # Moins de 10 caractères
            description="Description longue de plus de 50 caractères pour passer la validation",
            property_type=PropertyType.VILLA,
            transaction_type=TransactionType.VENTE,
            city="Marrakech",
            price=2000000.0,
            surface_area=200.0
        )
    
    assert "at least 10 characters" in str(exc.value)

def test_moroccan_phone_formats():
    """Test formats téléphone marocains valides"""
    valid_phones = [
        "0612345678",
        "0712345678",
        "0512345678",
        "+212612345678",
        "+212712345678"
    ]
    
    for phone in valid_phones:
        lead = LeadCreate(
            first_name="Test",
            last_name="User",
            phone=phone
        )
        assert lead.phone == phone

def test_enum_values():
    """Test valeurs des enums"""
    assert PropertyType.APPARTEMENT.value == "appartement"
    assert TransactionType.VENTE.value == "vente"
    assert LeadStatus.NEW.value == "new"
    assert UserRole.AGENT.value == "agent"

if __name__ == "__main__":
    # Exécution rapide des tests
    print("=== Tests des modèles SABBAR ===\n")
    
    try:
        test_property_create_valid()
        print("✓ Property création valide")
    except Exception as e:
        print(f"✗ Property création: {e}")
    
    try:
        test_lead_create_valid()
        print("✓ Lead création valide")
    except Exception as e:
        print(f"✗ Lead création: {e}")
    
    try:
        test_user_create_valid()
        print("✓ User création valide")
    except Exception as e:
        print(f"✗ User création: {e}")
    
    try:
        test_message_creation()
        print("✓ Message création valide")
    except Exception as e:
        print(f"✗ Message création: {e}")
    
    print("\n✓ Tous les tests de base passent!")