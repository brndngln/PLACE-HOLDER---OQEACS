from __future__ import annotations

from src.services.git_analyzer import GitAnalyzer


def test_history_from_existing_file(tmp_path) -> None:
    p = tmp_path / "a.py"
    p.write_text("def run():\n    pass", encoding="utf-8")
    out = GitAnalyzer().get_function_history(str(tmp_path), "a.py", "run")
    assert out.history


def test_history_missing_file(tmp_path) -> None:
    out = GitAnalyzer().get_function_history(str(tmp_path), "x.py", "run")
    assert out.history == []


def test_history_fields(tmp_path) -> None:
    p = tmp_path / "a.py"
    p.write_text("def run():\n    pass", encoding="utf-8")
    out = GitAnalyzer().get_function_history(str(tmp_path), "a.py", "run")
    assert out.function_name == "run"
