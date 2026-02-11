"""Initial schema for parallel-orchestrator"""

from __future__ import annotations

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS subtasks (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS merges (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS merges")
    op.execute("DROP TABLE IF EXISTS subtasks")
    op.execute("DROP TABLE IF EXISTS projects")
