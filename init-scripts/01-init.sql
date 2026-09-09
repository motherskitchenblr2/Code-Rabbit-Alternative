-- =============================================================================
# Git-Fix Database Initialization Script
# =============================================================================
# This script runs automatically when PostgreSQL container starts for the first time
# =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS gitfix;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
ALTER DATABASE gitfix SET search_path TO gitfix, public, audit;

-- =============================================================================
-- USERS & AUTHENTICATION
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'reviewer' CHECK (role IN ('admin', 'reviewer', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    two_factor_enabled BOOLEAN DEFAULT false,
    two_factor_secret VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON gitfix.users(email);
CREATE INDEX idx_users_username ON gitfix.users(username);
CREATE INDEX idx_users_role ON gitfix.users(role);
CREATE INDEX idx_users_active ON gitfix.users(is_active);

-- API Keys for programmatic access
CREATE TABLE IF NOT EXISTS gitfix.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_ip INET
);

CREATE INDEX idx_api_keys_user_id ON gitfix.api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON gitfix.api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON gitfix.api_keys(is_active);

-- Sessions
CREATE TABLE IF NOT EXISTS gitfix.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON gitfix.sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON gitfix.sessions(token_hash);
CREATE INDEX idx_sessions_expires ON gitfix.sessions(expires_at);

-- =============================================================================
-- REPOSITORIES
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id BIGINT UNIQUE,
    gitlab_id BIGINT,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(500) NOT NULL,
    description TEXT,
    private BOOLEAN DEFAULT true,
    default_branch VARCHAR(100) DEFAULT 'main',
    language VARCHAR(50),
    stars_count INTEGER DEFAULT 0,
    forks_count INTEGER DEFAULT 0,
    open_prs_count INTEGER DEFAULT 0,
    owner_id UUID REFERENCES gitfix.users(id) ON DELETE SET NULL,
    webhook_secret VARCHAR(255),
    webhook_id BIGINT,
    last_scan_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'idle' CHECK (status IN ('active', 'idle', 'error', 'archived')),
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE INDEX idx_repositories_github_id ON gitfix.repositories(github_id);
CREATE INDEX idx_repositories_owner_id ON gitfix.repositories(owner_id);
CREATE INDEX idx_repositories_status ON gitfix.repositories(status);
CREATE INDEX idx_repositories_full_name ON gitfix.repositories(full_name);

-- Repository members/permissions
CREATE TABLE IF NOT EXISTS gitfix.repository_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL REFERENCES gitfix.repositories(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'maintainer', 'reviewer', 'viewer')),
    invited_by UUID REFERENCES gitfix.users(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    UNIQUE(repository_id, user_id)
);

CREATE INDEX idx_repo_members_repo_id ON gitfix.repository_members(repository_id);
CREATE INDEX idx_repo_members_user_id ON gitfix.repository_members(user_id);

-- =============================================================================
-- PULL REQUESTS & REVIEWS
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.pull_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL REFERENCES gitfix.repositories(id) ON DELETE CASCADE,
    github_pr_id BIGINT UNIQUE,
    gitlab_pr_id BIGINT,
    number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    state VARCHAR(50) DEFAULT 'open' CHECK (state IN ('open', 'closed', 'merged', 'draft')),
    base_branch VARCHAR(100) NOT NULL,
    head_branch VARCHAR(100) NOT NULL,
    base_sha VARCHAR(40),
    head_sha VARCHAR(40),
    author_id UUID REFERENCES gitfix.users(id) ON DELETE SET NULL,
    author_login VARCHAR(100),
    is_draft BOOLEAN DEFAULT false,
    mergeable BOOLEAN,
    mergeable_state VARCHAR(50),
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    changed_files INTEGER DEFAULT 0,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prs_repo_id ON gitfix.pull_requests(repository_id);
CREATE INDEX idx_prs_github_id ON gitfix.pull_requests(github_pr_id);
CREATE INDEX idx_prs_state ON gitfix.pull_requests(state);
CREATE INDEX idx_prs_head_sha ON gitfix.pull_requests(head_sha);

-- Pipeline runs (each time a PR is analyzed)
CREATE TABLE IF NOT EXISTS gitfix.pipeline_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pull_request_id UUID NOT NULL REFERENCES gitfix.pull_requests(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) CHECK (trigger_type IN ('webhook', 'manual', 'scheduled', 'api')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    trigger_payload JSONB,
    error_message TEXT,
    error_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_pr_id ON gitfix.pipeline_runs(pull_request_id);
CREATE INDEX idx_pipeline_runs_status ON gitfix.pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started ON gitfix.pipeline_runs(started_at);

-- Pipeline stages
CREATE TABLE IF NOT EXISTS gitfix.pipeline_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES gitfix.pipeline_runs(id) ON DELETE CASCADE,
    stage_number INTEGER NOT NULL CHECK (stage_number BETWEEN 1 AND 5),
    stage_name VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    error_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stages_run_id ON gitfix.pipeline_stages(pipeline_run_id);
CREATE INDEX idx_stages_status ON gitfix.pipeline_stages(status);

-- =============================================================================
-- FINDINGS (Code Review Issues)
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id UUID NOT NULL REFERENCES gitfix.pipeline_runs(id) ON DELETE CASCADE,
    pull_request_id UUID NOT NULL REFERENCES gitfix.pull_requests(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL CHECK (finding_type IN ('security', 'logic', 'style', 'test', 'performance', 'documentation')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    category VARCHAR(100),
    cwe_id VARCHAR(20),
    file_path VARCHAR(500) NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    start_column INTEGER,
    end_column INTEGER,
    message TEXT NOT NULL,
    explanation TEXT,
    suggested_fix TEXT,
    confidence DECIMAL(3,2) CHECK (confidence >= 0 AND confidence <= 1),
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'fixed', 'false_positive', 'wont_fix', 'suppressed')),
    reporter VARCHAR(100) DEFAULT 'ai-critic',
    reviewer_id UUID REFERENCES gitfix.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_findings_run_id ON gitfix.findings(pipeline_run_id);
CREATE INDEX idx_findings_pr_id ON gitfix.findings(pull_request_id);
CREATE INDEX idx_findings_type ON gitfix.findings(finding_type);
CREATE INDEX idx_findings_severity ON gitfix.findings(severity);
CREATE INDEX idx_findings_status ON gitfix.findings(status);
CREATE INDEX idx_findings_file ON gitfix.findings(file_path);
CREATE INDEX idx_findings_created ON gitfix.findings(created_at);

-- Finding comments/discussions
CREATE TABLE IF NOT EXISTS gitfix.finding_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES gitfix.findings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_finding_comments_finding_id ON gitfix.finding_comments(finding_id);
CREATE INDEX idx_finding_comments_user_id ON gitfix.finding_comments(user_id);

-- =============================================================================
-- GITHUB INTEGRATION
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.github_installations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    installation_id BIGINT UNIQUE NOT NULL,
    account_login VARCHAR(255) NOT NULL,
    account_type VARCHAR(50),
    target_type VARCHAR(50),
    permissions JSONB DEFAULT '{}'::jsonb,
    repositories JSONB DEFAULT '[]'::jsonb,
    suspended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gitfix.webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    installation_id BIGINT NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    delivery_id VARCHAR(100),
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_events_installation ON gitfix.webhook_events(installation_id);
CREATE INDEX idx_webhook_events_processed ON gitfix.webhook_events(processed);
CREATE INDEX idx_webhook_events_type ON gitfix.webhook_events(event_type);

-- =============================================================================
-- AUDIT LOGGING
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    event_action VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES gitfix.users(id) ON DELETE SET NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    correlation_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit.audit_log(user_id);
CREATE INDEX idx_audit_log_resource ON audit.audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_event ON audit.audit_log(event_type, event_action);
CREATE INDEX idx_audit_log_created ON audit.audit_log(created_at);
CREATE INDEX idx_audit_log_correlation ON audit.audit_log(correlation_id);

-- =============================================================================
-- NOTIFICATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}'::jsonb,
    read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    action_url TEXT,
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON gitfix.notifications(user_id);
CREATE INDEX idx_notifications_read ON gitfix.notifications(read);
CREATE INDEX idx_notifications_created ON gitfix.notifications(created_at);

-- =============================================================================
-- WEBHOOK CONFIGURATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.webhook_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID REFERENCES gitfix.repositories(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES gitfix.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    events JSONB DEFAULT '[]'::jsonb,
    secret VARCHAR(255),
    active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    last_failure_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_configs_repo_id ON gitfix.webhook_configs(repository_id);
CREATE INDEX idx_webhook_configs_user_id ON gitfix.webhook_configs(user_id);

-- =============================================================================
-- METRICS & ANALYTICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS gitfix.daily_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    repository_id UUID REFERENCES gitfix.repositories(id) ON DELETE CASCADE,
    total_scans INTEGER DEFAULT 0,
    total_findings INTEGER DEFAULT 0,
    critical_findings INTEGER DEFAULT 0,
    high_findings INTEGER DEFAULT 0,
    medium_findings INTEGER DEFAULT 0,
    low_findings INTEGER DEFAULT 0,
    avg_scan_time_ms INTEGER,
    success_rate DECIMAL(5,2),
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, repository_id)
);

CREATE INDEX idx_daily_metrics_date ON gitfix.daily_metrics(date);
CREATE INDEX idx_daily_metrics_repo ON gitfix.daily_metrics(repository_id);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE gitfix.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.pull_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gitfix.findings ENABLE ROW LEVEL SECURITY;

-- Users can see their own data
CREATE POLICY users_own_data ON gitfix.users
    USING (id = current_user_id());

-- Users can see repositories they're members of
CREATE POLICY repo_members ON gitfix.repositories
    USING (id IN (SELECT repository_id FROM gitfix.repository_members WHERE user_id = current_user_id()));

-- Users can see PRs in their repositories
CREATE POLICY pr_repo_members ON gitfix.pull_requests
    USING (repository_id IN (SELECT repository_id FROM gitfix.repository_members WHERE user_id = current_user_id()));

-- Users can see findings in their repositories
CREATE POLICY findings_repo_members ON gitfix.findings
    USING (pull_request_id IN (
        SELECT id FROM gitfix.pull_requests 
        WHERE repository_id IN (
            SELECT repository_id FROM gitfix.repository_members WHERE user_id = current_user_id()
        )
    ));

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON gitfix.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON gitfix.repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pull_requests_updated_at BEFORE UPDATE ON gitfix.pull_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipeline_runs_updated_at BEFORE UPDATE ON gitfix.pipeline_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_findings_updated_at BEFORE UPDATE ON gitfix.findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON gitfix.notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_configs_updated_at BEFORE UPDATE ON gitfix.webhook_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Insert default admin user (password: gitfix2024!)
INSERT INTO gitfix.users (username, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    'admin',
    'admin@gitfix.io',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PZvO.S',
    'System Administrator',
    'admin',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Insert demo reviewer user (password: gitfix2024!)
INSERT INTO gitfix.users (username, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    'reviewer',
    'reviewer@gitfix.io',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PZvO.S',
    'Demo Reviewer',
    'reviewer',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Create default repository for demo
INSERT INTO gitfix.repositories (github_id, name, full_name, description, private, language, default_branch)
VALUES (
    0,
    'gitfix-demo',
    'demo/gitfix-demo',
    'Git-Fix demo repository for testing',
    true,
    'Python',
    'main'
) ON CONFLICT (github_id) DO NOTHING;

-- Grant demo user access to demo repo
INSERT INTO gitfix.repository_members (repository_id, user_id, role, accepted_at)
SELECT r.id, u.id, 'reviewer', NOW()
FROM gitfix.repositories r, gitfix.users u
WHERE r.name = 'gitfix-demo' AND u.username = 'reviewer'
ON CONFLICT DO NOTHING;

-- Grant admin user access to all repos
INSERT INTO gitfix.repository_members (repository_id, user_id, role, accepted_at)
SELECT r.id, u.id, 'admin', NOW()
FROM gitfix.repositories r, gitfix.users u
WHERE u.username = 'admin'
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMPLETION
-- =============================================================================

-- Grant permissions
GRANT USAGE ON SCHEMA gitfix TO PUBLIC;
GRANT USAGE ON SCHEMA audit TO PUBLIC;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gitfix TO gitfix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gitfix TO gitfix;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO gitfix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO gitfix;

-- Success message
\echo 'Git-Fix database initialized successfully!'
\echo 'Default users: admin@gitfix.io / gitfix2024! | reviewer@gitfix.io / gitfix2024!'