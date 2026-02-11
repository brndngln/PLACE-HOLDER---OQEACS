from __future__ import annotations

from src.models import NLRequest
from src.services.blueprint_generator import BlueprintGenerator


def test_generate_blueprint() -> None:
    req = NLRequest(description="Build a CRM API", tech_stack=["fastapi"], features=["auth"], constraints=[])
    bp = BlueprintGenerator().generate(req)
    assert bp.name


def test_endpoints_include_health() -> None:
    bp = BlueprintGenerator().generate(NLRequest(description="x", tech_stack=[], features=[], constraints=[]))
    assert "/health" in bp.api_endpoints


def test_estimated_files_positive() -> None:
    bp = BlueprintGenerator().generate(NLRequest(description="x", tech_stack=[], features=[], constraints=[]))
    assert bp.estimated_files > 0


def test_slugify() -> None:
    bp = BlueprintGenerator().generate(NLRequest(description="My Great App!!", tech_stack=[], features=[], constraints=[]))
    assert "-" in bp.name or bp.name == "my-great-app"
