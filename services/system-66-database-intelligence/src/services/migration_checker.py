from __future__ import annotations

from src.models import MigrationSafety


class MigrationChecker:
    def check_safety(self, sql: str) -> MigrationSafety:
        lower = sql.lower()
        risks: list[str] = []
        safe = True

        if "alter table" in lower:
            risks.append("ALTER TABLE may lock rows/table during migration")
            safe = False
        if "drop column" in lower or "drop table" in lower:
            risks.append("Destructive schema change detected")
            safe = False
        if "set not null" in lower and "default" not in lower:
            risks.append("NOT NULL change without DEFAULT may fail on existing rows")
            safe = False
        if "type" in lower and "alter table" in lower:
            risks.append("Column type change may require full table rewrite")

        lock = "high" if not safe else "low"
        rollback = "Use transactional DDL if supported and keep reverse ALTER script"
        return MigrationSafety(migration_sql=sql, safe=safe, risks=risks, estimated_lock_time=lock, rollback_plan=rollback)
