from __future__ import annotations

from src.services.opportunity_detector import OpportunityDetector


def test_detect_duplication() -> None:
    code = "a=1\na=1\na=1\n"
    out = OpportunityDetector().scan(code)
    assert any(o.type == "duplication" for o in out)


def test_detect_complex_conditionals() -> None:
    code = "if a:\n if b:\n  if c:\n   if d:\n    pass"
    out = OpportunityDetector().scan(code)
    assert any(o.type == "simplify_conditional" for o in out)


def test_detect_long_method() -> None:
    code = "\n".join(["x=1"] * 60)
    out = OpportunityDetector().scan(code)
    assert any(o.type == "extract_method" for o in out)


def test_returns_list() -> None:
    out = OpportunityDetector().scan("print('x')")
    assert isinstance(out, list)


def test_type_values_valid() -> None:
    out = OpportunityDetector().scan("print('x')")
    for o in out:
        assert o.type in {"dead_code", "duplication", "extract_method", "simplify_conditional", "extract_class", "inline_temp", "rename"}
