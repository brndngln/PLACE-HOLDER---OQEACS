"""Initial schema for regression-intelligence"""

from __future__ import annotations

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS comparisons (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS regression_rules (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS regression_rules")
    op.execute("DROP TABLE IF EXISTS comparisons")
    op.execute("DROP TABLE IF EXISTS snapshots")
