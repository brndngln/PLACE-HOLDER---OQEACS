from __future__ import annotations

from src.services.tree_builder import DependencyTreeBuilder


def test_parse_requirements(tmp_path) -> None:
    p = tmp_path / "requirements.txt"
    p.write_text("fastapi==0.115.6\nhttpx==0.28.1\n", encoding="utf-8")
    tree = DependencyTreeBuilder().build_tree(str(p))
    assert len(tree.nodes) == 2


def test_parse_package_lock(tmp_path) -> None:
    p = tmp_path / "package-lock.json"
    p.write_text('{"packages": {"": {}, "node_modules/react": {"version": "18.2.0"}}}', encoding="utf-8")
    tree = DependencyTreeBuilder().build_tree(str(p))
    assert any(n.name == "react" for n in tree.nodes)


def test_parse_cargo(tmp_path) -> None:
    p = tmp_path / "Cargo.lock"
    p.write_text('[[package]]\nname = "serde"\nversion = "1.0.200"\n', encoding="utf-8")
    tree = DependencyTreeBuilder().build_tree(str(p))
    assert any(n.name == "serde" for n in tree.nodes)


def test_missing_file() -> None:
    tree = DependencyTreeBuilder().build_tree("/tmp/nope.lock")
    assert tree.nodes == []


def test_cycle_flag_bool(tmp_path) -> None:
    p = tmp_path / "requirements.txt"
    p.write_text("a==1.0\n", encoding="utf-8")
    tree = DependencyTreeBuilder().build_tree(str(p))
    assert isinstance(tree.has_cycles, bool)
