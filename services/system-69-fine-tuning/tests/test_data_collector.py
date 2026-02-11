from __future__ import annotations

from src.models import CollectRequest
from src.services.data_collector import DataCollector


def test_collect_returns_entries() -> None:
    entries = DataCollector().collect(CollectRequest(source="code_reviews", days_back=7))
    assert len(entries) >= 1


def test_quality_filter() -> None:
    entries = DataCollector().collect(CollectRequest(source="bug_fixes", days_back=7))
    assert all(e.quality_score >= 0.8 for e in entries)


def test_has_instruction_fields() -> None:
    e = DataCollector().collect(CollectRequest(source="x", days_back=1))[0]
    assert e.instruction and e.output_text


def test_source_propagated() -> None:
    entries = DataCollector().collect(CollectRequest(source="test_results", days_back=2))
    assert all(e.source == "test_results" for e in entries)
