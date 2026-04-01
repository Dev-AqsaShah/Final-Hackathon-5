-- =============================================================================
-- CUSTOMER SUCCESS FTE - CRM/TICKET MANAGEMENT SYSTEM
-- =============================================================================
-- PostgreSQL schema for TechNova Customer Success FTE
-- This IS the CRM - tracks customers, conversations, tickets, messages
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for semantic search

-- =============================================================================
-- CUSTOMERS TABLE (unified across all channels)
-- =============================================================================
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(50),
    name            VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'
);

-- =============================================================================
-- CUSTOMER IDENTIFIERS (for cross-channel matching)
-- =============================================================================
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type  VARCHAR(50) NOT NULL,  -- 'email', 'phone', 'whatsapp'
    identifier_value VARCHAR(255) NOT NULL,
    verified         BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

-- =============================================================================
-- CONVERSATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel  VARCHAR(50) NOT NULL,  -- 'email', 'whatsapp', 'web_form'
    started_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at         TIMESTAMP WITH TIME ZONE,
    status           VARCHAR(50) DEFAULT 'active',  -- active, resolved, escalated, closed
    sentiment_score  DECIMAL(3,2),
    resolution_type  VARCHAR(50),  -- 'resolved', 'escalated', 'abandoned'
    escalated_to     VARCHAR(255),
    metadata         JSONB DEFAULT '{}'
);

-- =============================================================================
-- MESSAGES TABLE (with full channel tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID REFERENCES conversations(id) ON DELETE CASCADE,
    channel             VARCHAR(50) NOT NULL,       -- 'email', 'whatsapp', 'web_form'
    direction           VARCHAR(20) NOT NULL,        -- 'inbound', 'outbound'
    role                VARCHAR(20) NOT NULL,        -- 'customer', 'agent', 'system'
    content             TEXT NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tokens_used         INTEGER,
    latency_ms          INTEGER,
    tool_calls          JSONB DEFAULT '[]',
    channel_message_id  VARCHAR(255),               -- Gmail message ID, Twilio SID, etc.
    delivery_status     VARCHAR(50) DEFAULT 'pending'  -- pending, sent, delivered, failed
);

-- =============================================================================
-- TICKETS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE SET NULL,
    customer_id      UUID REFERENCES customers(id) ON DELETE CASCADE,
    source_channel   VARCHAR(50) NOT NULL,
    subject          VARCHAR(500),
    category         VARCHAR(100),
    priority         VARCHAR(20) DEFAULT 'medium',   -- low, medium, high, critical
    status           VARCHAR(50) DEFAULT 'open',      -- open, in_progress, resolved, escalated, closed
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at      TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    escalation_reason VARCHAR(200),
    escalation_team  VARCHAR(100),
    escalated_at     TIMESTAMP WITH TIME ZONE
);

-- =============================================================================
-- KNOWLEDGE BASE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(500) NOT NULL,
    content     TEXT NOT NULL,
    category    VARCHAR(100),
    embedding   VECTOR(1536),  -- OpenAI text-embedding-3-small dimensions
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- CHANNEL CONFIGURATIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS channel_configs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel              VARCHAR(50) UNIQUE NOT NULL,
    enabled              BOOLEAN DEFAULT TRUE,
    config               JSONB NOT NULL DEFAULT '{}',  -- API keys, webhook URLs
    response_template    TEXT,
    max_response_length  INTEGER,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- AGENT PERFORMANCE METRICS
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name   VARCHAR(100) NOT NULL,
    metric_value  DECIMAL(10,4) NOT NULL,
    channel       VARCHAR(50),  -- optional: channel-specific metrics
    dimensions    JSONB DEFAULT '{}',
    recorded_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- ESCALATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS escalations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID REFERENCES tickets(id) ON DELETE CASCADE,
    reason          VARCHAR(200) NOT NULL,
    team            VARCHAR(100) NOT NULL,
    urgency         VARCHAR(50) DEFAULT 'normal',
    assigned_to     VARCHAR(255),
    resolved        BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMP WITH TIME ZONE,
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(initial_channel);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(source_channel);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_name ON agent_metrics(metric_name, recorded_at DESC);

-- =============================================================================
-- SEED DATA: Channel Configurations
-- =============================================================================
INSERT INTO channel_configs (channel, enabled, config, max_response_length)
VALUES
    ('email',    TRUE, '{"provider": "gmail", "style": "formal"}', 2000),
    ('whatsapp', TRUE, '{"provider": "twilio", "style": "conversational"}', 1600),
    ('web_form', TRUE, '{"provider": "internal", "style": "semi_formal"}', 1000)
ON CONFLICT (channel) DO NOTHING;
