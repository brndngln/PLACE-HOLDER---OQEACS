from __future__ import annotations

from src.services.diagram_generator import DiagramGenerator


def test_generate_architecture_from_code() -> None:
    diag = DiagramGenerator().generate_architecture_from_code("import os\nfrom app.core import x")
    assert "graph TD" in diag.content


def test_diagram_type_mermaid() -> None:
    diag = DiagramGenerator().generate_architecture_from_code("print('x')")
    assert diag.type == "mermaid"


def test_generate_architecture_from_file(tmp_path) -> None:
    p = tmp_path / "a.py"
    p.write_text("import json", encoding="utf-8")
    diag = DiagramGenerator().generate_architecture(str(p))
    assert "Source" in diag.content
