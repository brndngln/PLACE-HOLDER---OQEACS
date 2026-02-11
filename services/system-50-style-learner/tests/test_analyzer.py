from __future__ import annotations

from src.services.analyzer import StyleAnalyzer


def test_detect_naming_snake_case(tmp_path) -> None:
    (tmp_path / "a.py").write_text("def my_func():\n    return 1\n", encoding="utf-8")
    profile = StyleAnalyzer().analyze_repo(str(tmp_path))
    assert profile.naming_convention == "snake_case"


def test_detect_import_style(tmp_path) -> None:
    (tmp_path / "a.py").write_text("import os\n\nfrom x import y\n", encoding="utf-8")
    profile = StyleAnalyzer().analyze_repo(str(tmp_path))
    assert profile.import_style in {"grouped", "inline"}


def test_detect_error_patterns(tmp_path) -> None:
    (tmp_path / "a.py").write_text("try:\n    x=1\nexcept Exception:\n    pass\n", encoding="utf-8")
    profile = StyleAnalyzer().analyze_repo(str(tmp_path))
    assert profile.error_pattern in {"typed_exceptions", "broad_exceptions"}


def test_detect_docstrings(tmp_path) -> None:
    (tmp_path / "a.py").write_text('"""module"""\ndef f():\n    return 1\n', encoding="utf-8")
    profile = StyleAnalyzer().analyze_repo(str(tmp_path))
    assert profile.docstring_style in {"triple_double", "triple_single"}


def test_detect_indentation(tmp_path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    profile = StyleAnalyzer().analyze_repo(str(tmp_path))
    assert profile.indent_style in {"spaces", "tabs"}
