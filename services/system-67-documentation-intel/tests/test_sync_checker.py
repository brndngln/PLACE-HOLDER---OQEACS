from __future__ import annotations

from src.services.sync_checker import SyncChecker


def test_sync_detects_missing_function_docs(tmp_path) -> None:
    code = tmp_path / "a.py"
    doc = tmp_path / "README.md"
    code.write_text("def run():\n    return 1\n", encoding="utf-8")
    doc.write_text("# Docs\n", encoding="utf-8")
    result = SyncChecker().check_sync(str(code), str(doc))
    assert result.in_sync is False


def test_sync_true_when_documented(tmp_path) -> None:
    code = tmp_path / "a.py"
    doc = tmp_path / "README.md"
    code.write_text("def run():\n    return 1\n", encoding="utf-8")
    doc.write_text("run", encoding="utf-8")
    result = SyncChecker().check_sync(str(code), str(doc))
    assert result.in_sync is True


def test_sync_handles_missing_files(tmp_path) -> None:
    result = SyncChecker().check_sync(str(tmp_path / "x.py"), str(tmp_path / "y.md"))
    assert result.in_sync is True


def test_sync_stale_sections_list() -> None:
    result = SyncChecker().check_sync("/tmp/nope.py", "/tmp/nope.md")
    assert isinstance(result.stale_sections, list)
