from __future__ import annotations

from src.services.version_manager import PromptVersionManager


def test_create_version() -> None:
    mgr = PromptVersionManager()
    v = mgr.create_version("core", "sys", "tmpl")
    assert v.version == 1


def test_list_versions() -> None:
    mgr = PromptVersionManager()
    mgr.create_version("core", "sys", "tmpl")
    assert len(mgr.list_versions()) == 1


def test_get_version() -> None:
    mgr = PromptVersionManager()
    v = mgr.create_version("core", "sys", "tmpl")
    assert mgr.get_version(v.id) is not None


def test_rollback() -> None:
    mgr = PromptVersionManager()
    mgr.create_version("core", "sys", "tmpl")
    assert mgr.rollback("core", 1) is not None
