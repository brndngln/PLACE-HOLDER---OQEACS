"""Scan router: endpoints for dependency scanning and package info."""

from __future__ import annotations

from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query

from src.config import settings
from src.models import (
    APIChange,
    DependencyScanRequest,
    PackageQuery,
    PackageRegistry,
    ScanResult,
)
from src.services.lockfile_parser import LockfileParser
from src.services.registry_scanner import RegistryScanner
from src.services.scheduler import register_tracked_packages
from src.services.upgrade_planner import UpgradePlanner

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.post("/scan", response_model=ScanResult)
async def scan_project(request: DependencyScanRequest) -> ScanResult:
    """Scan a project's dependencies from its lockfile.

    Parses the specified lockfile to extract all dependencies with their
    current versions, then scans each package against its registry for
    updates, breaking changes, and security advisories. Finally, generates
    an upgrade plan ordered by dependency topology.
    """
    logger.info(
        "scan_requested",
        project_path=request.project_path,
        lockfile_type=request.lockfile_type,
    )

    parser = LockfileParser()

    # Read lockfile content
    try:
        with open(request.project_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Lockfile not found: {request.project_path}",
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied reading: {request.project_path}",
        )

    # Parse lockfile based on type
    registry_map = {
        "requirements.txt": ("pypi", parser.parse_requirements_txt),
        "package-lock.json": ("npm", parser.parse_package_lock),
        "Cargo.lock": ("crates", parser.parse_cargo_lock),
        "go.sum": ("go", parser.parse_go_sum),
        "pom.xml": ("maven", lambda c: []),  # Maven parsing not yet implemented
    }

    registry_type, parse_fn = registry_map.get(
        request.lockfile_type, ("pypi", parser.parse_requirements_txt)
    )
    parsed_packages = parse_fn(content)

    if not parsed_packages:
        return ScanResult(
            packages=[],
            total_outdated=0,
            total_breaking=0,
            total_security=0,
            upgrade_plan=[],
            scanned_at=datetime.utcnow(),
        )

    # Build scan input
    scan_input = [
        {"name": name, "registry": registry_type, "current_version": version}
        for name, version in parsed_packages
    ]

    # Register packages for periodic tracking
    register_tracked_packages(scan_input)

    # Scan all packages
    async with httpx.AsyncClient(timeout=30.0) as client:
        scanner = RegistryScanner(http_client=client)
        planner = UpgradePlanner(http_client=client)

        scanned = await scanner.scan_all(scan_input)

        total_outdated = sum(1 for p in scanned if p.is_outdated)
        total_breaking = sum(1 for p in scanned if p.breaking_changes)
        total_security = sum(1 for p in scanned if p.security_advisories)

        # Build scan result for upgrade planning
        scan_result = ScanResult(
            packages=scanned,
            total_outdated=total_outdated,
            total_breaking=total_breaking,
            total_security=total_security,
            upgrade_plan=[],
            scanned_at=datetime.utcnow(),
        )

        # Generate upgrade plan
        upgrade_plan = await planner.plan_upgrades(scan_result)
        scan_result.upgrade_plan = upgrade_plan

    logger.info(
        "scan_complete",
        total_packages=len(scanned),
        outdated=total_outdated,
        breaking=total_breaking,
        security=total_security,
    )

    return scan_result


@router.get("/packages/{name}", response_model=PackageRegistry)
async def get_package_info(
    name: str,
    registry: str = Query(default="pypi", description="Registry to query"),
    current_version: str = Query(default="0.0.0", description="Installed version"),
) -> PackageRegistry:
    """Get the latest information about a single package.

    Queries the specified registry for the package's current release
    information, version comparison, and security advisories.
    """
    logger.info("package_info_requested", package=name, registry=registry)

    async with httpx.AsyncClient(timeout=30.0) as client:
        scanner = RegistryScanner(http_client=client)

        if registry == "pypi":
            result = await scanner.scan_pypi(name, current_version)
        elif registry == "npm":
            result = await scanner.scan_npm(name, current_version)
        elif registry == "crates":
            result = await scanner.scan_crates(name, current_version)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported registry: {registry}. Supported: pypi, npm, crates",
            )

    return result


@router.get("/packages/{name}/changes", response_model=list[APIChange])
async def get_package_changes(
    name: str,
    from_version: str = Query(..., description="Current version"),
    to_version: str = Query(default="latest", description="Target version"),
    registry: str = Query(default="pypi", description="Registry"),
) -> list[APIChange]:
    """Get detailed API changes between two versions of a package.

    Fetches the changelog or release notes from the registry and uses
    LLM-powered analysis to extract structured change information
    including breaking changes, deprecations, and migration guides.
    """
    logger.info(
        "changes_requested",
        package=name,
        from_version=from_version,
        to_version=to_version,
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        scanner = RegistryScanner(http_client=client)

        # First resolve "latest" to actual version
        if to_version == "latest":
            if registry == "pypi":
                pkg = await scanner.scan_pypi(name, from_version)
            elif registry == "npm":
                pkg = await scanner.scan_npm(name, from_version)
            elif registry == "crates":
                pkg = await scanner.scan_crates(name, from_version)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported registry: {registry}",
                )
            to_version = pkg.latest_version

        # Get changelog for the package
        if registry == "pypi":
            url = f"{settings.PYPI_URL}/pypi/{name}/json"
        elif registry == "npm":
            url = f"{settings.NPM_REGISTRY_URL}/{name}"
        else:
            return []  # Crates.io doesn't have inline changelogs

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("changelog_fetch_failed", package=name, error=str(exc))
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch package data: {exc}",
            )

        # Extract description/readme for changelog parsing
        if registry == "pypi":
            text = data.get("info", {}).get("description", "")
        else:
            text = data.get("readme", "")

        if not text:
            return []

        changes = await scanner._parse_changelog(text, from_version, to_version, name)

    return changes
