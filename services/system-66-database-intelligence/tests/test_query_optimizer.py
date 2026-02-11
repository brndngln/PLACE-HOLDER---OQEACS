from __future__ import annotations

from src.services.query_optimizer import QueryOptimizer


def test_detect_select_star() -> None:
    result = QueryOptimizer().analyze_query("SELECT * FROM users")
    assert any("SELECT *" in s for s in result.suggestions)


def test_detect_missing_where() -> None:
    result = QueryOptimizer().analyze_query("DELETE FROM users")
    assert any("WHERE" in s for s in result.suggestions)


def test_detect_like_wildcard() -> None:
    result = QueryOptimizer().analyze_query("SELECT id FROM t WHERE name LIKE '%abc'")
    assert any("wildcard" in s for s in result.suggestions)


def test_index_recommendation() -> None:
    result = QueryOptimizer().analyze_query("SELECT id FROM t WHERE user_id = 1")
    assert result.index_recommendations


def test_cost_non_negative() -> None:
    result = QueryOptimizer().analyze_query("SELECT 1")
    assert result.estimated_cost >= 0
