"""Initial schema for social-media"""
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE TABLE IF NOT EXISTS social_accounts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50) NOT NULL, account_handle VARCHAR(200) NOT NULL, follower_count INTEGER DEFAULT 0, following_count INTEGER DEFAULT 0, post_count INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS posts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, status VARCHAR(50) DEFAULT "draft", content_format VARCHAR(50) DEFAULT "text", text_content TEXT, media_urls JSONB DEFAULT "[]"::jsonb, hashtags JSONB DEFAULT "[]"::jsonb, scheduled_at TIMESTAMPTZ, published_at TIMESTAMPTZ, platform_post_id VARCHAR(200), impressions INTEGER DEFAULT 0, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, saves INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, engagement_rate DECIMAL(7,4) DEFAULT 0, virality_score DECIMAL(5,2) DEFAULT 0, content_pillar VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS content_pillars (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(100) NOT NULL, target_percentage DECIMAL(5,2), actual_percentage DECIMAL(5,2) DEFAULT 0, avg_engagement_rate DECIMAL(7,4) DEFAULT 0, post_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS posting_schedules (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, day_of_week INTEGER NOT NULL, optimal_time TIME NOT NULL, timezone VARCHAR(50) DEFAULT "UTC", created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_accounts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50) NOT NULL, account_handle VARCHAR(200) NOT NULL, follower_count INTEGER DEFAULT 0, avg_engagement_rate DECIMAL(7,4) DEFAULT 0, content_strategy_summary TEXT, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS competitor_posts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), competitor_account_id UUID NOT NULL, text_content TEXT, content_format VARCHAR(50), posted_at TIMESTAMPTZ, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, engagement_rate DECIMAL(7,4) DEFAULT 0, is_viral BOOLEAN DEFAULT FALSE, captured_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS trends (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), platform VARCHAR(50), topic VARCHAR(300) NOT NULL, hashtag VARCHAR(200), category VARCHAR(100), relevance_score DECIMAL(3,2), recommended_action TEXT, source VARCHAR(100), detected_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS engagement_queue (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, interaction_type VARCHAR(50) NOT NULL, content TEXT, sentiment VARCHAR(20), priority INTEGER DEFAULT 5, status VARCHAR(20) DEFAULT "pending", suggested_response TEXT, actual_response TEXT, responded_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS follower_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, follower_count INTEGER NOT NULL, snapshot_date DATE NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())')
    op.execute('CREATE TABLE IF NOT EXISTS growth_milestones (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL, platform VARCHAR(50) NOT NULL, milestone_value INTEGER NOT NULL, reached_at TIMESTAMPTZ NOT NULL, celebrated BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW())')

def downgrade() -> None:
    for table in ["growth_milestones","follower_snapshots","engagement_queue","trends","competitor_posts","competitor_accounts","posting_schedules","content_pillars","posts","social_accounts"]:
        op.execute(f'DROP TABLE IF EXISTS {table}')
