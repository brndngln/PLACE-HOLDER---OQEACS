#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        MCP PACKAGE REGISTRY SERVICE                           ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice exposes a minimal package registry API for verifying the   ║
║ existence of packages and versions, retrieving available versions and        ║
║ dependencies, and checking version compatibility with a given Python        ║
║ version.  It interfaces with the public PyPI JSON API and caches responses  ║
║ in Redis with a 24‑hour TTL to reduce latency and external calls.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from redis.asyncio import Redis


# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class RegistryStatus(str):
    """Enumeration of registry operation statuses."""

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class PackageExistResponse(BaseModel):
    """Response model for package existence checks."""

    status: RegistryStatus = Field(...)
    exists: bool = Field(...)
    message: Optional[str] = Field(None)


class PackageVersionsResponse(BaseModel):
    """Response model listing available versions."""

    status: RegistryStatus = Field(...)
    versions: List[str] = Field(default_factory=list)


class PackageDependenciesResponse(BaseModel):
    """Response model for dependencies."""

    status: RegistryStatus = Field(...)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Mapping of dependency to version spec")


class VersionCompatibilityResponse(BaseModel):
    """Response model for version compatibility checks."""

    status: RegistryStatus = Field(...)
    compatible: bool = Field(...)
    reason: Optional[str] = Field(None)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class PackageRegistryService:
    """Business logic for package registry operations."""

    redis: Redis
    cache_ttl: int = 86400  # 24 hours
    session: aiohttp.ClientSession = dataclasses.field(init=False)
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    request_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.session = aiohttp.ClientSession()
        self.logger = structlog.get_logger(__name__).bind(component="package_registry_service")
        self.request_counter = Counter(
            "package_registry_requests_total", "Total package registry requests"
        )
        self.latency_histogram = Histogram(
            "package_registry_latency_seconds",
            "Package registry request latency",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
        )

    async def close(self) -> None:
        await self.session.close()

    async def _fetch_pypi(self, package: str) -> Optional[Dict[str, any]]:
        url = f"https://pypi.org/pypi/{package}/json"
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as exc:  # noqa: B902
            self.logger.warning("pypi_fetch_error", package=package, error=str(exc))
            return None

    async def _get_cached_or_fetch(self, cache_key: str, fetcher) -> Optional[Dict[str, any]]:
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                return eval(cached)  # uses python literal syntax; safe given we control writes
            except Exception:
                # fallback to fresh fetch if cache corrupted
                pass
        data = await fetcher()
        if data is not None:
            await self.redis.set(cache_key, repr(data), ex=self.cache_ttl)
        return data

    async def check_exists(self, package: str, version: Optional[str] = None) -> PackageExistResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            key = f"pkg:{package}"
            data = await self._get_cached_or_fetch(key, lambda: self._fetch_pypi(package))
            if not data:
                return PackageExistResponse(status=RegistryStatus.NOT_FOUND, exists=False, message="Package not found")
            if version:
                exists = version in data.get("releases", {})
                return PackageExistResponse(status=RegistryStatus.OK if exists else RegistryStatus.NOT_FOUND, exists=exists)
            return PackageExistResponse(status=RegistryStatus.OK, exists=True)

    async def get_versions(self, package: str) -> PackageVersionsResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            key = f"pkg:{package}"
            data = await self._get_cached_or_fetch(key, lambda: self._fetch_pypi(package))
            if not data:
                return PackageVersionsResponse(status=RegistryStatus.NOT_FOUND, versions=[])
            releases = data.get("releases", {})
            versions = sorted(releases.keys(), reverse=True)
            return PackageVersionsResponse(status=RegistryStatus.OK, versions=versions)

    async def get_dependencies(self, package: str, version: Optional[str]) -> PackageDependenciesResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            key = f"pkg:{package}"
            data = await self._get_cached_or_fetch(key, lambda: self._fetch_pypi(package))
            if not data:
                return PackageDependenciesResponse(status=RegistryStatus.NOT_FOUND, dependencies={})
            releases = data.get("releases", {})
            # Determine version: latest if none specified
            target_version = version or data.get("info", {}).get("version")
            release_files = releases.get(target_version, [])
            # Look for first wheel or sdist metadata
            requires_dist: List[str] = []
            # Many packages duplicate dependencies across distributions. Instead, use info field when available.
            requires_dist = data.get("info", {}).get("requires_dist") or []
            deps: Dict[str, str] = {}
            for item in requires_dist:
                # Format: "package_name (version_spec) ; extra == '...'"
                parts = item.split(";")[0].strip()
                if "(" in parts:
                    name, spec = parts.split("(", 1)
                    spec = spec.strip(")")
                else:
                    name, spec = parts, ""
                deps[name.strip()] = spec.strip()
            return PackageDependenciesResponse(status=RegistryStatus.OK, dependencies=deps)

    async def check_compatibility(self, package: str, version: str, python_version: str) -> VersionCompatibilityResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            key = f"pkg:{package}"
            data = await self._get_cached_or_fetch(key, lambda: self._fetch_pypi(package))
            if not data:
                return VersionCompatibilityResponse(status=RegistryStatus.NOT_FOUND, compatible=False, reason="Package not found")
            releases = data.get("releases", {})
            release_files = releases.get(version)
            if not release_files:
                return VersionCompatibilityResponse(status=RegistryStatus.NOT_FOUND, compatible=False, reason="Version not found")
            # Evaluate requires_python from metadata
            requires_python = None
            for file in release_files:
                if file.get("requires_python"):
                    requires_python = file["requires_python"]
                    break
            if not requires_python:
                # assume compatible when unspecified
                return VersionCompatibilityResponse(status=RegistryStatus.OK, compatible=True)
            # Simple semver check: if python_version startswith required prefix
            # requires_python may contain specifiers like ">=3.8"
            compatible = True
            reason = None
            if requires_python.startswith(">="):
                min_py = requires_python[2:]
                if tuple(map(int, python_version.split("."))) < tuple(map(int, min_py.split("."))):
                    compatible = False
                    reason = f"Requires Python {requires_python}"
            elif requires_python:
                # exact match or prefix requirement
                if not python_version.startswith(requires_python):
                    compatible = False
                    reason = f"Requires Python {requires_python}"
            return VersionCompatibilityResponse(status=RegistryStatus.OK if compatible else RegistryStatus.ERROR, compatible=compatible, reason=reason)


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    redis_host = os.getenv("REDIS_HOST", "omni-redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_password = os.getenv("REDIS_PASSWORD", None)
    redis_client = Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password, encoding="utf-8", decode_responses=True)
    service = PackageRegistryService(redis=redis_client)
    app = FastAPI(title="MCP Package Registry", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/api/v1/check_package_exists", response_model=PackageExistResponse)
    async def check_package_exists(package: str = Query(..., description="Package name"), version: Optional[str] = Query(None, description="Specific version to check")) -> PackageExistResponse:
        return await service.check_exists(package, version)

    @app.get("/api/v1/get_package_versions", response_model=PackageVersionsResponse)
    async def get_package_versions(package: str = Query(..., description="Package name")) -> PackageVersionsResponse:
        return await service.get_versions(package)

    @app.get("/api/v1/get_package_dependencies", response_model=PackageDependenciesResponse)
    async def get_package_dependencies(package: str = Query(..., description="Package name"), version: Optional[str] = Query(None, description="Specific version")) -> PackageDependenciesResponse:
        return await service.get_dependencies(package, version)

    @app.get("/api/v1/check_version_compatibility", response_model=VersionCompatibilityResponse)
    async def check_version_compatibility(package: str = Query(..., description="Package name"), version: str = Query(..., description="Package version"), python_version: str = Query(..., description="Python version e.g. 3.11")) -> VersionCompatibilityResponse:
        return await service.check_compatibility(package, version, python_version)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        try:
            # Perform a quick ping to Redis
            await service.redis.ping()
        except Exception:
            raise HTTPException(status_code=503, detail="Redis unavailable")
        return {"status": "ready"}

    return app


app = create_app()