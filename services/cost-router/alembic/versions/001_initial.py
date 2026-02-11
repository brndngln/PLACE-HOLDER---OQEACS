"""Initial schema for cost-router"""

from __future__ import annotations

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS classifications (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS cost_tracking (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS cost_events (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cost_events")
    op.execute("DROP TABLE IF EXISTS cost_tracking")
    op.execute("DROP TABLE IF EXISTS classifications")
