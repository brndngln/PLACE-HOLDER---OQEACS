from __future__ import annotations

from src.services.parser import CodeParser


def test_parse_simple_function(tmp_path) -> None:
    path = tmp_path / "a.py"
    path.write_text("def add(a,b):\\n    return a+b\\n", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "python")
    assert any(e.name == "add" for e in entities)


def test_parse_class_with_methods(tmp_path) -> None:
    path = tmp_path / "m.py"
    path.write_text("class A:\\n    def run(self):\\n        return 1\\n", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "python")
    assert any(e.name == "A" for e in entities)


def test_parse_imports(tmp_path) -> None:
    path = tmp_path / "i.py"
    path.write_text("import os\\nfrom sys import path\\n", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "python")
    assert any(e.entity_type.value == "import" for e in entities)


def test_parse_typescript_interface(tmp_path) -> None:
    path = tmp_path / "i.ts"
    path.write_text("interface X { id: number }\\nexport function f(){ return 1 }", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "typescript")
    assert len(entities) >= 1


def test_handle_syntax_error(tmp_path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("def x(:\\n    pass", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "python")
    assert isinstance(entities, list)


def test_empty_file(tmp_path) -> None:
    path = tmp_path / "e.py"
    path.write_text("", encoding="utf-8")
    parser = CodeParser()
    entities = parser.parse_file(str(path), "python")
    assert entities == []
