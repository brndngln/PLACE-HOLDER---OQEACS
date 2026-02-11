from __future__ import annotations

from src.models import ErrorEvent
from src.services.fix_generator import FixGenerator


def _event(msg: str) -> ErrorEvent:
    return ErrorEvent(service="svc", error_type="runtime", message=msg, timestamp="now")


def test_generate_keyerror_fix() -> None:
    fix = FixGenerator().generate_fix(_event("KeyError: x"), "code")
    assert "key not in data" in fix


def test_generate_typeerror_fix() -> None:
    fix = FixGenerator().generate_fix(_event("TypeError: none"), "code")
    assert "value is None" in fix


def test_generate_timeout_fix() -> None:
    fix = FixGenerator().generate_fix(_event("Timeout"), "code")
    assert "retry" in fix


def test_generate_default_fix() -> None:
    fix = FixGenerator().generate_fix(_event("Other"), "code")
    assert "defensive" in fix
