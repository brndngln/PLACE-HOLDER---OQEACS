"""Upgrade planning and compatibility routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from src.models import CompatibilityMatrix, ScanResult, UpgradePlan
from src.services.compatibility_checker import CompatibilityChecker
from src.services.upgrade_planner import UpgradePlanner

router = APIRouter(prefix="/api/v1", tags=["upgrades"])


@router.post("/upgrade-plan", response_model=list[UpgradePlan])
async def upgrade_plan(scan_result: ScanResult) -> list[UpgradePlan]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        planner = UpgradePlanner(http_client=client)
        return await planner.plan_upgrades(scan_result)


@router.get("/compatibility/{pkg_a}/{pkg_b}", response_model=CompatibilityMatrix)
async def compatibility(
    pkg_a: str,
    pkg_b: str,
    ver_a: str,
    ver_b: str,
) -> CompatibilityMatrix:
    async with httpx.AsyncClient(timeout=30.0) as client:
        checker = CompatibilityChecker(http_client=client)
        return await checker.check_compatibility(pkg_a, ver_a, pkg_b, ver_b)


@router.post("/compatibility/matrix", response_model=list[CompatibilityMatrix])
async def compatibility_matrix(packages: list[dict[str, str]]) -> list[CompatibilityMatrix]:
    if len(packages) < 2:
        raise HTTPException(status_code=422, detail="At least two packages required")
    async with httpx.AsyncClient(timeout=30.0) as client:
        checker = CompatibilityChecker(http_client=client)
        return await checker.build_matrix(packages)
