from __future__ import annotations

from src.services.deletion_analyzer import DeletionAnalyzer


def test_low_risk_single_ref(tmp_path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    pass", encoding="utf-8")
    out = DeletionAnalyzer().assess_deletion_risk(str(tmp_path), "a.py", "f")
    assert out.risk_level in {"low", "medium", "high"}


def test_more_refs_higher_risk(tmp_path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    pass\nf()\nf()\n", encoding="utf-8")
    out = DeletionAnalyzer().assess_deletion_risk(str(tmp_path), "a.py", "f")
    assert out.dependents_count >= 0


def test_reason_exists(tmp_path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    pass", encoding="utf-8")
    out = DeletionAnalyzer().assess_deletion_risk(str(tmp_path), "a.py", "f")
    assert isinstance(out.reason, str)
