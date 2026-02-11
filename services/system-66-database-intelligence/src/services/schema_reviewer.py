from __future__ import annotations

import re

from src.models import SchemaReview


class SchemaReviewer:
    def review(self, schema_sql: str) -> SchemaReview:
        tables = re.findall(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-zA-Z0-9_]+)", schema_sql, flags=re.I)
        issues: list[str] = []
        recs: list[str] = []

        for table in tables:
            block = self._extract_table_block(schema_sql, table)
            if "primary key" not in block.lower():
                issues.append(f"Table `{table}` has no PRIMARY KEY")
            if "created_at" not in block.lower():
                recs.append(f"Add created_at timestamp to `{table}`")
            if "updated_at" not in block.lower():
                recs.append(f"Add updated_at timestamp to `{table}`")
            if re.search(r"varchar\s*\(\s*\)", block, flags=re.I):
                issues.append(f"Invalid VARCHAR length in `{table}`")

            fk_cols = re.findall(r"([a-zA-Z0-9_]+)_id\s", block)
            for col in fk_cols:
                if f"index ({col}_id" not in schema_sql.lower() and f"index {col}_id" not in schema_sql.lower():
                    recs.append(f"Consider index on `{table}.{col}_id`")

        score = max(0.0, round(100 - len(issues) * 15 - len(recs) * 2, 2))
        return SchemaReview(tables=tables, issues=issues, score=score, recommendations=recs)

    @staticmethod
    def _extract_table_block(sql: str, table: str) -> str:
        m = re.search(rf"create\s+table\s+(?:if\s+not\s+exists\s+)?{table}\s*\((.*?)\);", sql, flags=re.I | re.S)
        return m.group(1) if m else ""
