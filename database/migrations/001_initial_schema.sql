-- database/migrations/001_initial_schema.sql

-- Extension pour UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table Users (Agents)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL DEFAULT 'agent' CHECK (role IN ('admin', 'agent', 'manager')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    
    -- Profil
    bio TEXT,
    avatar_url TEXT,
    specialties TEXT[], -- Array de spécialités
    cities_covered TEXT[], -- Villes couvertes
    
    -- Stats
    properties_count INTEGER DEFAULT 0,
    leads_count INTEGER DEFAULT 0,
    conversions_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Table Properties (Annonces)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Informations de base
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    property_type TEXT NOT NULL CHECK (property_type IN (
        'appartement', 'villa', 'maison', 'terrain', 'riad',
        'bureau', 'local_commercial', 'immeuble'
    )),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'vente', 'location', 'location_vacances'
    )),
    status TEXT NOT NULL DEFAULT 'disponible' CHECK (status IN (
        'disponible', 'reserve', 'vendu', 'loue', 'retire'
    )),
    
    -- Localisation
    city TEXT NOT NULL,
    district TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    
    -- Caractéristiques
    price NUMERIC(12,2) NOT NULL,
    surface_area NUMERIC(10,2) NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    
    -- Équipements (boolean)
    parking BOOLEAN DEFAULT FALSE,
    elevator BOOLEAN DEFAULT FALSE,
    garden BOOLEAN DEFAULT FALSE,
    pool BOOLEAN DEFAULT FALSE,
    security BOOLEAN DEFAULT FALSE,
    furnished BOOLEAN DEFAULT FALSE,
    
    -- Médias
    images TEXT[], -- Array d'URLs
    main_image TEXT,
    
    -- Statistiques
    views_count INTEGER DEFAULT 0,
    favorites_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Contact
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    
    -- Recherche
    property_type TEXT,
    transaction_type TEXT CHECK (transaction_type IN ('vente', 'location', 'location_vacances')), -- ✅ AJOUTÉ
    budget_min NUMERIC(12,2),
    budget_max NUMERIC(12,2),
    preferred_cities TEXT[],
    preferred_districts TEXT[],
    min_bedrooms INTEGER,
    min_surface NUMERIC(10,2),
    
    -- Statut
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN (
        'new', 'contacted', 'qualified', 'interested',
        'negotiation', 'converted', 'lost', 'unqualified'
    )),
    
    -- Notes et qualification IA
    notes TEXT,
    ai_qualification_score NUMERIC(5,2),
    ai_qualification_summary TEXT,
    ai_extracted_data JSONB,
    
    -- Propriétés liées
    interested_properties UUID[], -- Array d'IDs
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_contact_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ
);

-- Table Conversations (Historique IA)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    session_id TEXT UNIQUE NOT NULL,
    
    -- Statut
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'completed', 'abandoned'
    )),
    
    -- Messages (JSONB pour flexibilité)
    messages JSONB DEFAULT '[]'::jsonb,
    
    -- Métadonnées
    user_ip TEXT,
    user_agent TEXT,
    
    -- Qualification
    qualification_completed BOOLEAN DEFAULT FALSE,
    qualification_data JSONB,
    
    -- Statistiques
    message_count INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
-- Modifier la table conversations
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS prospect_name TEXT,
ADD COLUMN IF NOT EXISTS prospect_phone TEXT CHECK (prospect_phone IS NULL OR prospect_phone ~ '^(\+212|0)[5-7][0-9]{8}$'),
ADD COLUMN IF NOT EXISTS prospect_email TEXT CHECK (prospect_email IS NULL OR prospect_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
ADD COLUMN IF NOT EXISTS extracted_criteria JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS qualification_score NUMERIC(5,2);

-- Table Messages (historique des messages d'une conversation)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'function')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
-- Index pour performances
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_agent ON properties(agent_id);

CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_priority ON leads(priority);
CREATE INDEX idx_leads_agent ON leads(agent_id);
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_phone ON leads(phone);

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_lead ON conversations(lead_id);
CREATE INDEX idx_conversations_status ON conversations(status);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Fonction pour auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers pour updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policies de base (à affiner selon besoins)
CREATE POLICY "Enable read for authenticated users" ON properties
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all for service role" ON properties
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');