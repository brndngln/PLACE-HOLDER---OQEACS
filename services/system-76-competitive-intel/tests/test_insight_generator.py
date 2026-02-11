from __future__ import annotations

from src.services.insight_generator import InsightGenerator


def test_get_insights() -> None:
    out = InsightGenerator().get_insights("api")
    assert out.implementations


def test_best_practices_present() -> None:
    out = InsightGenerator().get_insights("api")
    assert out.best_practices


def test_trends_present() -> None:
    out = InsightGenerator().get_insights("api")
    assert out.trends
