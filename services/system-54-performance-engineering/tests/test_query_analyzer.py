from __future__ import annotations

from src.services.query_analyzer import QueryAnalyzer


def test_detect_select_star() -> None:
    out = QueryAnalyzer().detect_n_plus_one("SELECT * FROM users")
    assert any(x.pattern == "select_star" for x in out)


def test_detect_update_without_where() -> None:
    out = QueryAnalyzer().detect_n_plus_one("UPDATE users SET name='a'")
    assert any(x.pattern == "update_without_where" for x in out)


def test_detect_delete_without_where() -> None:
    out = QueryAnalyzer().detect_n_plus_one("DELETE FROM users")
    assert any(x.pattern == "delete_without_where" for x in out)


def test_detect_loop_query_pattern() -> None:
    code = "for i in items:\n    session.query(User).filter(User.id==i).first()"
    out = QueryAnalyzer().detect_n_plus_one(code)
    assert any(x.pattern == "loop_with_query" for x in out)
