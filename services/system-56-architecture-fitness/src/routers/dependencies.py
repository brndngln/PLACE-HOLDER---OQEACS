from __future__ import annotations

from fastapi import APIRouter

from src.services.dependency_checker import DependencyChecker

router = APIRouter(prefix="/api/v1/dependencies", tags=["dependencies"])


@router.post("/check")
def check(payload: dict):
    rules = payload.get("rules", [])
    imports_map = payload.get("imports_map", {})
    from src.models import DependencyRule

    parsed_rules = [DependencyRule(**r) for r in rules]
    return DependencyChecker().check_dependencies(parsed_rules, imports_map)


@router.post("/circular")
def circular(imports_map: dict[str, list[str]]):
    return DependencyChecker().detect_circular_dependencies(imports_map)


@router.get("/circular-deps")
def circular_empty():
    return []
