from __future__ import annotations

from src.services.verification import FixVerifier


def test_verify_false_when_same() -> None:
    assert FixVerifier().verify_fix("x", "x") is False


def test_verify_false_without_marker() -> None:
    assert FixVerifier().verify_fix("x", "y") is False


def test_verify_true_with_marker() -> None:
    assert FixVerifier().verify_fix("x", "y\n# auto-fix") is True


def test_verify_handles_empty() -> None:
    assert FixVerifier().verify_fix("", "# auto-fix") is True
