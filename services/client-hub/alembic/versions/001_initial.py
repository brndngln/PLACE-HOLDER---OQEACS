"""Initial schema for client-hub"""

from __future__ import annotations

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS deliveries (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS activity_log (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_log")
    op.execute("DROP TABLE IF EXISTS deliveries")
    op.execute("DROP TABLE IF EXISTS approvals")
    op.execute("DROP TABLE IF EXISTS projects")
