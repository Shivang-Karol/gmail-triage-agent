-- The core queue structure designed for high resiliency and no duplicate processing.

CREATE TABLE IF NOT EXISTS emails (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT,
    received_at TIMESTAMP,
    
    -- Processing State
    status TEXT DEFAULT 'pending', -- pending, leased, completed, failed, dead_letter
    attempt_count INTEGER DEFAULT 0,
    
    -- Locking (Concurrency Control)
    lease_owner TEXT,           -- UUID of the worker claiming the job
    lease_expires_at TIMESTAMP, -- When the lease expires if the worker crashes
    next_attempt_at TIMESTAMP,  -- Exponential backoff timer
    
    -- Diagnostics
    last_error TEXT,            -- The exception message if it failed
    
    -- Output Storage
    classification_json TEXT,   -- Structured output from Gemini
    model_name TEXT,            
    model_latency_ms INTEGER,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices to make scanning the queue fast even if you have thousands of records
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_next_attempt ON emails(next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_emails_lease_expiry ON emails(lease_expires_at);

-- A simple key-value store to keep our Gmail Sync Checkpoint
CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily API call counter to enforce cost guardrails
CREATE TABLE IF NOT EXISTS api_usage (
    date TEXT PRIMARY KEY,  -- YYYY-MM-DD
    call_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
