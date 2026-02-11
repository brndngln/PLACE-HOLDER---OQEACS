from __future__ import annotations

from fastapi import APIRouter

from src.models import ContractChange
from src.services.graph_builder import ServiceGraphBuilder
from src.services.impact_analyzer import CrossRepoImpactAnalyzer
from src.services.migration_generator import MigrationGenerator

router = APIRouter(prefix="/api/v1", tags=["impact"])


@router.post("/impact")
def impact(payload: dict):
    changed = payload.get("changed_service")
    changes = [ContractChange(**c) for c in payload.get("changes", [])]
    graph = ServiceGraphBuilder().build_graph(payload.get("services_dir", "services"))
    return CrossRepoImpactAnalyzer().analyze_impact(changed, changes, graph)


@router.post("/migrate")
def migrate(payload: dict):
    changed = payload.get("changed_service")
    changes = [ContractChange(**c) for c in payload.get("changes", [])]
    graph = ServiceGraphBuilder().build_graph(payload.get("services_dir", "services"))
    impact_map = CrossRepoImpactAnalyzer().analyze_impact(changed, changes, graph)
    return MigrationGenerator().generate_migrations(impact_map, changes)


@router.get("/changes/{service}")
def changes(service: str):
    return {"service": service, "changes": []}
