from __future__ import annotations

from src.services.sql_analyzer import SQLAnalyzer


def test_select_star() -> None:
    issues = SQLAnalyzer().analyze("SELECT * FROM users")
    assert any(i.rule_id == "SQL-SELECT-STAR" for i in issues)


def test_update_without_where() -> None:
    issues = SQLAnalyzer().analyze("UPDATE users SET name='x'")
    assert any(i.rule_id == "SQL-WHERE" for i in issues)


def test_injection_concat() -> None:
    issues = SQLAnalyzer().analyze("query = 'SELECT * FROM users WHERE id=' + user_id")
    assert any(i.rule_id == "SQL-INJECTION" for i in issues)


def test_like_wildcard() -> None:
    issues = SQLAnalyzer().analyze("SELECT id FROM t WHERE name LIKE '%abc'")
    assert any(i.rule_id == "SQL-LIKE" for i in issues)
