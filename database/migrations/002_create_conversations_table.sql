-- Migration pour créer la table conversations dans Supabase
-- Cette table stocke les conversations de l'agent IA avec les prospects

CREATE TABLE IF NOT EXISTS conversations (
    -- Identifiant unique (UUID)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- État complet de la conversation (JSONB pour flexibilité)
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Métadonnées pour requêtes rapides
    qualification_score INTEGER DEFAULT 0 CHECK (qualification_score >= 0 AND qualification_score <= 100),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    
    -- Relation avec le lead créé (si applicable)
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_lead_id ON conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_qualification_score ON conversations(qualification_score DESC);

-- Index GIN pour recherche dans le JSONB
CREATE INDEX IF NOT EXISTS idx_conversations_state_gin ON conversations USING GIN (state);

-- Fonction trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour updated_at
DROP TRIGGER IF EXISTS conversations_updated_at_trigger ON conversations;
CREATE TRIGGER conversations_updated_at_trigger
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_updated_at();

-- Commentaires pour documentation
COMMENT ON TABLE conversations IS 'Historique des conversations avec l''agent IA de qualification';
COMMENT ON COLUMN conversations.id IS 'Identifiant unique de la conversation (UUID)';
COMMENT ON COLUMN conversations.state IS 'État complet de la conversation (messages, critères, contact, etc.)';
COMMENT ON COLUMN conversations.qualification_score IS 'Score de qualification du prospect (0-100)';
COMMENT ON COLUMN conversations.status IS 'Statut de la conversation (active, completed, abandoned)';
COMMENT ON COLUMN conversations.lead_id IS 'ID du lead créé suite à cette conversation';
COMMENT ON COLUMN conversations.created_at IS 'Date de création de la conversation';
COMMENT ON COLUMN conversations.updated_at IS 'Date de dernière mise à jour';

-- Exemple de structure du champ state (JSONB)
/*
{
  "conversation_id": "uuid",
  "messages": [
    {
      "role": "user|assistant",
      "content": "texte du message",
      "timestamp": "ISO 8601"
    }
  ],
  "criteria": {
    "preferred_cities": ["Casablanca"],
    "preferred_types": ["appartement"],
    "transaction_type": "vente",
    "budget_min": 1500000,
    "budget_max": 2000000,
    "rooms": 3,
    "area": 120
  },
  "contact_info": {
    "name": "Mohamed Alami",
    "phone": "+212612345678",
    "email": "mohamed@example.com"
  },
  "qualification_score": 75,
  "lead_quality": "hot|warm|cold",
  "status": "active|completed",
  "lead_id": "uuid ou null",
  "created_at": "ISO 8601",
  "user_id": "uuid de l'agent immobilier",
  "ended_at": "ISO 8601",
  "end_reason": "completed|abandoned|error"
}
*/

-- Politique RLS (Row Level Security) - À adapter selon vos besoins
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Exemple de politique : Tous peuvent lire et écrire (À SÉCURISER en production !)
CREATE POLICY "conversations_allow_all" ON conversations
    FOR ALL
    TO public
    USING (true)
    WITH CHECK (true);

-- En production, utilisez une politique plus restrictive comme :
-- CREATE POLICY "conversations_user_access" ON conversations
--     FOR ALL
--     TO authenticated
--     USING (user_id = auth.uid() OR auth.role() = 'admin')
--     WITH CHECK (user_id = auth.uid() OR auth.role() = 'admin');
