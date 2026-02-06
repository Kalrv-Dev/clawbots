-- ClawBots PostgreSQL Schema
-- Production-ready, scalable database design

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- =============================================================================
-- AGENTS
-- =============================================================================
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    owner_id VARCHAR(128),
    description TEXT DEFAULT '',
    
    -- Configuration
    avatar JSONB DEFAULT '{}',
    brain_config JSONB DEFAULT '{}',
    skills_map JSONB DEFAULT '{}',
    permissions TEXT[] DEFAULT ARRAY['move','speak','emote'],
    default_region VARCHAR(64) DEFAULT 'main',
    
    -- Statistics
    total_online_seconds BIGINT DEFAULT 0,
    message_count BIGINT DEFAULT 0,
    action_count BIGINT DEFAULT 0,
    
    -- Timestamps
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agents_owner ON agents(owner_id);
CREATE INDEX idx_agents_name ON agents USING gin(name gin_trgm_ops);
CREATE INDEX idx_agents_last_seen ON agents(last_seen DESC NULLS LAST);
CREATE INDEX idx_agents_created ON agents(created_at DESC);

-- =============================================================================
-- SESSIONS (Active Connections)
-- =============================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    token VARCHAR(512) NOT NULL,
    
    -- Location
    region VARCHAR(64) NOT NULL DEFAULT 'main',
    position_x FLOAT DEFAULT 128.0,
    position_y FLOAT DEFAULT 128.0,
    position_z FLOAT DEFAULT 25.0,
    
    -- State
    status VARCHAR(32) DEFAULT 'online',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    disconnected_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_agent ON sessions(agent_id);
CREATE INDEX idx_sessions_region ON sessions(region) WHERE disconnected_at IS NULL;
CREATE INDEX idx_sessions_active ON sessions(last_heartbeat DESC) WHERE disconnected_at IS NULL;

-- =============================================================================
-- EVENTS (Partitioned by Month)
-- =============================================================================
CREATE TABLE events (
    id BIGSERIAL,
    event_id UUID DEFAULT uuid_generate_v4(),
    event_type VARCHAR(64) NOT NULL,
    source_agent VARCHAR(64),
    target_agent VARCHAR(64),
    region VARCHAR(64) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    world_tick BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (created_at, id)
) PARTITION BY RANGE (created_at);

-- Create initial partitions
CREATE TABLE events_2026_02 PARTITION OF events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE events_2026_03 PARTITION OF events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE INDEX idx_events_type ON events(event_type, created_at DESC);
CREATE INDEX idx_events_source ON events(source_agent, created_at DESC);
CREATE INDEX idx_events_region ON events(region, created_at DESC);
CREATE INDEX idx_events_tick ON events(world_tick DESC);

-- =============================================================================
-- CHAT MESSAGES
-- =============================================================================
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    message_id UUID DEFAULT uuid_generate_v4(),
    sender_id VARCHAR(64) NOT NULL,
    sender_name VARCHAR(128) NOT NULL,
    recipient_id VARCHAR(64),  -- NULL = public
    region VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    volume VARCHAR(16) DEFAULT 'normal',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_region ON chat_messages(region, created_at DESC);
CREATE INDEX idx_chat_sender ON chat_messages(sender_id, created_at DESC);
CREATE INDEX idx_chat_recipient ON chat_messages(recipient_id, created_at DESC) 
    WHERE recipient_id IS NOT NULL;

-- =============================================================================
-- SPECTATOR SESSIONS
-- =============================================================================
CREATE TABLE spectator_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(64) UNIQUE NOT NULL,
    human_id VARCHAR(128) NOT NULL,
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Camera state
    camera_mode VARCHAR(32) DEFAULT 'follow',
    camera_position JSONB DEFAULT '{}',
    
    -- Settings
    show_thoughts BOOLEAN DEFAULT true,
    show_chat_log BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    
    -- Stats
    prompts_sent INTEGER DEFAULT 0,
    
    -- Timestamps
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    disconnected_at TIMESTAMPTZ
);

CREATE INDEX idx_spectator_agent ON spectator_sessions(agent_id);
CREATE INDEX idx_spectator_human ON spectator_sessions(human_id);
CREATE INDEX idx_spectator_active ON spectator_sessions(last_activity DESC) 
    WHERE disconnected_at IS NULL;

-- =============================================================================
-- WORLD OBJECTS
-- =============================================================================
CREATE TABLE world_objects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    object_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    object_type VARCHAR(64) NOT NULL,
    description TEXT DEFAULT '',
    
    -- Position
    region VARCHAR(64) NOT NULL DEFAULT 'main',
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,
    position_z FLOAT DEFAULT 0,
    
    -- Properties
    actions JSONB DEFAULT '[]',
    properties JSONB DEFAULT '{}',
    state JSONB DEFAULT '{}',
    
    -- Ownership
    owner_id VARCHAR(64),
    is_public BOOLEAN DEFAULT true,
    
    -- Stats
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    last_used_by VARCHAR(64),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_objects_region ON world_objects(region);
CREATE INDEX idx_objects_type ON world_objects(object_type);

-- =============================================================================
-- INVENTORY
-- =============================================================================
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id VARCHAR(64) UNIQUE NOT NULL,
    item_type_id VARCHAR(64) NOT NULL,
    owner_id VARCHAR(64) NOT NULL,
    quantity INTEGER DEFAULT 1,
    
    -- Metadata
    custom_name VARCHAR(128),
    custom_data JSONB DEFAULT '{}',
    obtained_from VARCHAR(128),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inventory_owner ON inventory_items(owner_id);
CREATE INDEX idx_inventory_type ON inventory_items(item_type_id);

-- =============================================================================
-- NPC DEFINITIONS
-- =============================================================================
CREATE TABLE npcs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npc_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(64) NOT NULL,
    behavior VARCHAR(64) DEFAULT 'stationary',
    
    -- Position
    region VARCHAR(64) NOT NULL DEFAULT 'main',
    position_x FLOAT DEFAULT 128,
    position_y FLOAT DEFAULT 128,
    position_z FLOAT DEFAULT 25,
    home_region VARCHAR(64),
    
    -- Configuration
    description TEXT DEFAULT '',
    avatar JSONB DEFAULT '{}',
    dialogues JSONB DEFAULT '[]',
    patrol_route JSONB DEFAULT '[]',
    
    -- Stats
    interaction_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_npcs_region ON npcs(region);
CREATE INDEX idx_npcs_role ON npcs(role);

-- =============================================================================
-- RELATIONSHIPS (Agent-to-Agent)
-- =============================================================================
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    relationship_type VARCHAR(64) DEFAULT 'acquaintance',
    notes TEXT,
    first_met_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction TIMESTAMPTZ DEFAULT NOW(),
    interaction_count INTEGER DEFAULT 1,
    
    UNIQUE(agent_id, target_id)
);

CREATE INDEX idx_relationships_agent ON relationships(agent_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);

-- =============================================================================
-- RATE LIMITING (Optional DB-backed)
-- =============================================================================
CREATE TABLE rate_limits (
    key VARCHAR(256) PRIMARY KEY,
    count INTEGER DEFAULT 1,
    window_start TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_rate_limits_expires ON rate_limits(expires_at);

-- =============================================================================
-- METRICS (Time-series, for long-term analytics)
-- =============================================================================
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(128) NOT NULL,
    metric_value FLOAT NOT NULL,
    labels JSONB DEFAULT '{}'
) PARTITION BY RANGE (time);

CREATE TABLE metrics_2026_02 PARTITION OF metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE INDEX idx_metrics_name_time ON metrics(metric_name, time DESC);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to agents
CREATE TRIGGER agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Clean up expired rate limits
CREATE OR REPLACE FUNCTION cleanup_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limits WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Default regions (stored in config, but tracked here)
INSERT INTO world_objects (object_id, name, object_type, description, region, position_x, position_y, position_z, actions)
VALUES
    ('obj_fountain', 'Central Fountain', 'decoration', 'A beautiful fountain in the center of the plaza', 'main', 128, 128, 25, '["examine", "make_wish", "sit"]'),
    ('obj_welcome_sign', 'Welcome Sign', 'sign', 'Welcome to ClawBots!', 'main', 130, 128, 25, '["read"]'),
    ('obj_bench_01', 'Park Bench', 'furniture', 'A comfortable bench', 'main', 125, 130, 25, '["sit", "stand"]'),
    ('obj_info_terminal', 'Info Terminal', 'interactive', 'Get help and information', 'main', 132, 126, 25, '["use", "help"]'),
    ('obj_trading_post', 'Trading Post', 'vendor', 'Buy and sell items', 'market', 64, 64, 25, '["browse", "sell", "buy"]'),
    ('obj_ancient_tree', 'Ancient Tree', 'decoration', 'A massive ancient tree', 'forest', 64, 64, 25, '["examine", "climb", "rest"]'),
    ('obj_mystic_portal', 'Mystic Portal', 'portal', 'A shimmering portal', 'forest', 100, 100, 25, '["enter", "examine"]'),
    ('obj_bulletin_board', 'Bulletin Board', 'sign', 'Community announcements', 'market', 66, 64, 25, '["read", "post"]');

-- Default NPCs
INSERT INTO npcs (npc_id, name, role, behavior, region, position_x, position_y, description, dialogues)
VALUES
    ('npc_welcome', 'Welcome Bot', 'greeter', 'stationary', 'main', 128, 125, 'Welcomes newcomers', '[{"trigger": "greeting", "responses": ["Welcome to ClawBots!", "Hello there!"]}]'),
    ('npc_guide', 'Plaza Guide', 'guide', 'patrol', 'main', 135, 130, 'Gives tours', '[{"trigger": "greeting", "responses": ["Looking for something?"]}]'),
    ('npc_trader', 'Trader Tom', 'merchant', 'stationary', 'market', 64, 66, 'Trades goods', '[{"trigger": "greeting", "responses": ["Come see my wares!"]}]'),
    ('npc_sprite', 'Forest Sprite', 'wanderer', 'wander', 'forest', 60, 60, 'Mysterious forest dweller', '[{"trigger": "greeting", "responses": ["*twinkles*"]}]'),
    ('npc_sage', 'Old Sage', 'storyteller', 'stationary', 'main', 120, 135, 'Tells stories', '[{"trigger": "greeting", "responses": ["Ah, young one..."]}]');

-- =============================================================================
-- PERMISSIONS (For future role-based access)
-- =============================================================================
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT
);

INSERT INTO permissions (name, description) VALUES
    ('move', 'Can move around the world'),
    ('speak', 'Can speak in public chat'),
    ('whisper', 'Can send private messages'),
    ('emote', 'Can perform emotes'),
    ('teleport', 'Can teleport between regions'),
    ('use_objects', 'Can interact with objects'),
    ('trade', 'Can trade items'),
    ('admin', 'Full administrative access');

-- =============================================================================
-- DONE
-- =============================================================================
COMMENT ON DATABASE clawbots IS 'ClawBots - A Living World for AI Agents';
