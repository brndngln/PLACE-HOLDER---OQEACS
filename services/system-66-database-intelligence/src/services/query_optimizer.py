from __future__ import annotations

import re

from src.models import IndexRecommendation, QueryAnalysis


class QueryOptimizer:
    def analyze_query(self, sql: str) -> QueryAnalysis:
        s = sql.strip()
        lower = s.lower()
        suggestions: list[str] = []
        indexes: list[IndexRecommendation] = []

        if re.search(r"select\s+\*", lower):
            suggestions.append("Avoid SELECT * in production queries")
        if (lower.startswith("update") or lower.startswith("delete")) and "where" not in lower:
            suggestions.append("Mutation query missing WHERE clause")
        if " like '%" in lower:
            suggestions.append("Leading wildcard LIKE prevents index use")
        if re.search(r"where\s+([a-zA-Z0-9_]+)\s*=", lower):
            col = re.search(r"where\s+([a-zA-Z0-9_]+)\s*=", lower).group(1)
            indexes.append(IndexRecommendation(table="unknown", columns=[col], type="btree", reason="Equality filter", estimated_improvement="medium"))
        if "::" in s:
            suggestions.append("Implicit/explicit casts may hurt index usage")

        cost = 10.0 + len(suggestions) * 7.5
        return QueryAnalysis(query=s, execution_plan_summary="Heuristic static analysis", estimated_cost=cost, suggestions=suggestions, index_recommendations=indexes)
