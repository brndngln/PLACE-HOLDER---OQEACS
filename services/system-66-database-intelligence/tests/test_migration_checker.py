from __future__ import annotations

from src.services.migration_checker import MigrationChecker


def test_alter_table_risk() -> None:
    out = MigrationChecker().check_safety("ALTER TABLE users ADD COLUMN x INT;")
    assert out.safe is False


def test_drop_column_risk() -> None:
    out = MigrationChecker().check_safety("ALTER TABLE users DROP COLUMN x;")
    assert out.risks


def test_not_null_without_default() -> None:
    out = MigrationChecker().check_safety("ALTER TABLE users ALTER COLUMN x SET NOT NULL;")
    assert any("NOT NULL" in r for r in out.risks)


def test_safe_sql() -> None:
    out = MigrationChecker().check_safety("CREATE INDEX idx_users_email ON users(email);")
    assert out.safe is True
