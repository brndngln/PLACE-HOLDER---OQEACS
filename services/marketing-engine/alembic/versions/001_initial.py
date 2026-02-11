"""Initial schema for marketing-engine"""
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE TABLE IF NOT EXISTS campaigns (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, campaign_type VARCHAR(50) NOT NULL, status VARCHAR(50) NOT NULL DEFAULT "draft", channels JSONB DEFAULT "[]"::jsonb, budget_total DECIMAL(12,2) DEFAULT 0, budget_spent DECIMAL(12,2) DEFAULT 0, goal_target INTEGER DEFAULT 0, goal_achieved INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_variants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, variant_label VARCHAR(10), channel VARCHAR(50), headline TEXT, body_copy TEXT, cta_text VARCHAR(200), impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS leads (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) UNIQUE NOT NULL, source VARCHAR(50), status VARCHAR(50) DEFAULT "new", score INTEGER DEFAULT 0, score_breakdown JSONB DEFAULT "{}"::jsonb, company_size INTEGER, job_title VARCHAR(200), industry VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS lead_activities (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), lead_id UUID NOT NULL, activity_type VARCHAR(50) NOT NULL, metadata JSONB DEFAULT "{}"::jsonb, score_delta INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS audiences (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, segment_rules JSONB DEFAULT "[]"::jsonb, member_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS email_sequences (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, name VARCHAR(200) NOT NULL, trigger_event VARCHAR(100), status VARCHAR(50) DEFAULT "draft", created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS email_sequence_steps (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), sequence_id UUID NOT NULL, step_number INTEGER NOT NULL, delay_hours INTEGER DEFAULT 24, subject_line TEXT, body_html TEXT, sent_count INTEGER DEFAULT 0, open_count INTEGER DEFAULT 0, click_count INTEGER DEFAULT 0, unsubscribe_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS landing_pages (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, slug VARCHAR(200) UNIQUE NOT NULL, title VARCHAR(300) NOT NULL, html_content TEXT NOT NULL, status VARCHAR(20) DEFAULT "draft", views INTEGER DEFAULT 0, submissions INTEGER DEFAULT 0, conversion_rate DECIMAL(5,4) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_calendar (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), title VARCHAR(300) NOT NULL, content_type VARCHAR(50) NOT NULL, channel VARCHAR(50) NOT NULL, scheduled_date DATE NOT NULL, status VARCHAR(20) DEFAULT "planned", content_brief TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitors (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, website VARCHAR(500), description TEXT, pricing_model TEXT, target_market TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), competitor_id UUID NOT NULL, snapshot_type VARCHAR(50), content TEXT, changes_detected TEXT, analyzed_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS campaign_metrics (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID NOT NULL, metric_date DATE NOT NULL, impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, leads_generated INTEGER DEFAULT 0, revenue_attributed DECIMAL(12,2) DEFAULT 0, cost DECIMAL(12,2) DEFAULT 0, roi DECIMAL(8,2) DEFAULT 0, channel VARCHAR(50), created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS funnel_stages (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id UUID, name VARCHAR(100), stage_order INTEGER, entries INTEGER DEFAULT 0, exits INTEGER DEFAULT 0, conversions INTEGER DEFAULT 0, drop_off_rate DECIMAL(5,4) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')

def downgrade() -> None:
    for table in ["funnel_stages","campaign_metrics","competitor_snapshots","competitors","content_calendar","landing_pages","email_sequence_steps","email_sequences","audiences","lead_activities","leads","content_variants","campaigns"]:
        op.execute(f'DROP TABLE IF EXISTS {table}')
