from __future__ import annotations

from src.services.quality_scorer import TestQualityScorer


def test_detect_assert_true_issue() -> None:
    score = TestQualityScorer().score_test_file("def test_x():\n    assert True")
    assert any("assert True" in i for i in score.issues)


def test_no_assertions_issue() -> None:
    score = TestQualityScorer().score_test_file("def test_x():\n    pass")
    assert any("No assertions" in i for i in score.issues)


def test_total_tests_count() -> None:
    score = TestQualityScorer().score_test_file("def test_a():\n assert 1\n\ndef test_b():\n assert 2")
    assert score.total_tests == 2


def test_score_bounds() -> None:
    score = TestQualityScorer().score_test_file("def test_x():\n    assert 1")
    assert 0 <= score.quality_score <= 100
