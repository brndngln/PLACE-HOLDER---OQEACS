CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(200) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(200) NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    source_ip VARCHAR(45),
    trace_id VARCHAR(100),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_events(trace_id) WHERE trace_id IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'audit_logger_user') THEN
        CREATE ROLE audit_logger_user LOGIN PASSWORD 'change-me-via-vault';
    END IF;
END $$;

REVOKE UPDATE, DELETE ON audit_events FROM audit_logger_user;
GRANT INSERT, SELECT ON audit_events TO audit_logger_user;
