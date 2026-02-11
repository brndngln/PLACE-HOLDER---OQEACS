from __future__ import annotations

from src.models import ErrorPattern
from src.services.pattern_matcher import PatternMatcher


def test_signature_computation() -> None:
    m = PatternMatcher({})
    sig = m.compute_signature("ValueError: bad", "line 10")
    assert len(sig) > 10


def test_match_known_error() -> None:
    pattern = ErrorPattern(id="1", language="python", error_type="ValueError", pattern_signature="a" * 24, description="x")
    m = PatternMatcher({"1": pattern})
    out = m.match_error("x", "")
    assert isinstance(out, list)


def test_no_match_for_unknown() -> None:
    m = PatternMatcher({})
    assert m.match_error("unknown", "") == []


def test_similarity_ranking() -> None:
    p1 = ErrorPattern(id="1", language="python", error_type="A", pattern_signature="a" * 24, description="a")
    p2 = ErrorPattern(id="2", language="python", error_type="B", pattern_signature="b" * 24, description="b")
    m = PatternMatcher({"1": p1, "2": p2})
    out = m.match_error("aaaa", "")
    assert isinstance(out, list)


def test_empty_input() -> None:
    m = PatternMatcher({})
    out = m.match_error("", "")
    assert out == []
