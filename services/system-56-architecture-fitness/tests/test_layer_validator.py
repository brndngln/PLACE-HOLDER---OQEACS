from __future__ import annotations

from src.models import LayerDefinition
from src.services.layer_validator import LayerValidator


def test_layer_violation_detected() -> None:
    layers = [
        LayerDefinition(name="controllers", allowed_dependencies=["services"]),
        LayerDefinition(name="services", allowed_dependencies=["repositories"]),
    ]
    imports = {"controllers/api.py": ["repositories.user"]}
    out = LayerValidator().validate_layers(layers, imports)
    assert len(out) == 1


def test_layer_allowed() -> None:
    layers = [LayerDefinition(name="controllers", allowed_dependencies=["services"])]
    imports = {"controllers/api.py": ["services.user"]}
    out = LayerValidator().validate_layers(layers, imports)
    assert out == []


def test_unknown_layer_skipped() -> None:
    layers = [LayerDefinition(name="controllers", allowed_dependencies=["services"])]
    imports = {"misc/tool.py": ["x.y"]}
    out = LayerValidator().validate_layers(layers, imports)
    assert out == []


def test_multiple_imports() -> None:
    layers = [LayerDefinition(name="controllers", allowed_dependencies=["services"])]
    imports = {"controllers/api.py": ["services.a", "repositories.b"]}
    out = LayerValidator().validate_layers(layers, imports)
    assert len(out) == 1
