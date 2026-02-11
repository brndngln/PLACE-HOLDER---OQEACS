"""Tests for spec generator annotation extraction."""
from src.services.spec_generator import SpecGenerator, SPEC_PROMPTS
from src.config import Settings


def test_all_tools_have_prompts():
    expected_tools = ["crosshair", "tla_plus", "dafny", "cbmc", "spin", "kani", "alloy"]
    for tool in expected_tools:
        assert tool in SPEC_PROMPTS, f"Missing prompt for {tool}"


def test_extract_annotations_python():
    settings = Settings()
    gen = SpecGenerator(settings)
    spec = """
def add(a: int, b: int) -> int:
    assert a >= 0  # pre: non-negative
    result = a + b
    assert result >= a  # post: no overflow
    return result
"""
    annotations = gen._extract_annotations(spec, "crosshair")
    assert len(annotations) >= 2


def test_extract_annotations_tla():
    settings = Settings()
    gen = SpecGenerator(settings)
    spec = """
THEOREM Safety == []TypeInvariant
INVARIANT NoDeadlock
PROPERTY EventualProgress
"""
    annotations = gen._extract_annotations(spec, "tla_plus")
    assert len(annotations) >= 2


def test_extract_annotations_dafny():
    settings = Settings()
    gen = SpecGenerator(settings)
    spec = """
method Max(a: int, b: int) returns (r: int)
    requires true
    ensures r >= a && r >= b
    decreases *
{
    if a >= b { r := a; } else { r := b; }
}
"""
    annotations = gen._extract_annotations(spec, "dafny")
    assert len(annotations) >= 2
