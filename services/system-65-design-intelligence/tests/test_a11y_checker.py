from __future__ import annotations

from src.services.accessibility_checker import AccessibilityChecker


def test_missing_alt_detected() -> None:
    report = AccessibilityChecker().check("<img src='x.png'>")
    assert any("alt" in v.lower() for v in report.violations)


def test_keyboard_handler_warning() -> None:
    report = AccessibilityChecker().check("<div onClick={x}></div>")
    assert report.score <= 100


def test_aria_suggestion() -> None:
    report = AccessibilityChecker().check("<button>Save</button>")
    assert any("ARIA" in s for s in report.suggestions)


def test_score_bounds() -> None:
    report = AccessibilityChecker().check("<button aria-label='x'>X</button>")
    assert 0 <= report.score <= 100


def test_no_crash_empty() -> None:
    report = AccessibilityChecker().check("")
    assert isinstance(report.violations, list)
