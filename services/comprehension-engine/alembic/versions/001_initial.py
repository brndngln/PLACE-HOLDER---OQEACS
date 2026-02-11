"""Initial schema for comprehension-engine"""

from __future__ import annotations

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS analysis_files (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS analysis_patterns (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS analysis_conventions (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")
    op.execute("""CREATE TABLE IF NOT EXISTS analysis_profiles (id TEXT PRIMARY KEY, payload JSONB, created_at TIMESTAMPTZ DEFAULT NOW())""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS analysis_profiles")
    op.execute("DROP TABLE IF EXISTS analysis_conventions")
    op.execute("DROP TABLE IF EXISTS analysis_patterns")
    op.execute("DROP TABLE IF EXISTS analysis_files")
    op.execute("DROP TABLE IF EXISTS analyses")
