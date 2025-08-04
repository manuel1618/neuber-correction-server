-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    last_activity TIMESTAMP,
    request_count INTEGER DEFAULT 0,
    ip_address TEXT
);

-- Rate limiting table  
CREATE TABLE rate_limits (
    key TEXT PRIMARY KEY,  -- IP or session_id
    requests INTEGER DEFAULT 0,
    window_start TIMESTAMP
);

-- Usage analytics
CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    endpoint TEXT,
    duration_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    timestamp TIMESTAMP,
    ip_address TEXT
);