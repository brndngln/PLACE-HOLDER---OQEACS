from __future__ import annotations

from src.services.schema_reviewer import SchemaReviewer


def test_detect_missing_pk() -> None:
    review = SchemaReviewer().review("CREATE TABLE users (id INT, name TEXT);")
    assert any("PRIMARY KEY" in i for i in review.issues)


def test_detect_table_name() -> None:
    review = SchemaReviewer().review("CREATE TABLE accounts (id SERIAL PRIMARY KEY);")
    assert "accounts" in review.tables


def test_recommend_timestamps() -> None:
    review = SchemaReviewer().review("CREATE TABLE a (id SERIAL PRIMARY KEY);")
    assert any("created_at" in r for r in review.recommendations)


def test_score_bounds() -> None:
    review = SchemaReviewer().review("CREATE TABLE t (id SERIAL PRIMARY KEY, created_at TIMESTAMP, updated_at TIMESTAMP);")
    assert 0 <= review.score <= 100


def test_empty_schema() -> None:
    review = SchemaReviewer().review("")
    assert review.tables == []
