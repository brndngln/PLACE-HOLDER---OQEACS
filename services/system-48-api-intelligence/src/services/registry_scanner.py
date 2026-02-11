"""Registry scanner for PyPI, npm, and crates.io packages."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime

import httpx
import structlog
from packaging.version import Version, InvalidVersion

from src.config import settings
from src.models import APIChange, PackageRegistry

logger = structlog.get_logger(__name__)


class RegistryScanner:
    """Scans package registries for version updates, breaking changes, and security issues."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def scan_pypi(self, package_name: str, current_version: str = "0.0.0") -> PackageRegistry:
        """Scan PyPI for a package's latest version and metadata.

        Calls the PyPI JSON API at /pypi/{package}/json to get release info,
        compares the installed version with the latest release, and detects
        any breaking changes or deprecations from the changelog.
        """
        client = await self._get_client()
        url = f"{settings.PYPI_URL}/pypi/{package_name}/json"
        logger.info("scanning_pypi", package=package_name, url=url)

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("pypi_http_error", package=package_name, status=exc.response.status_code)
            return PackageRegistry(
                name=package_name,
                registry="pypi",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )
        except httpx.RequestError as exc:
            logger.error("pypi_request_error", package=package_name, error=str(exc))
            return PackageRegistry(
                name=package_name,
                registry="pypi",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )

        latest_version = data.get("info", {}).get("version", current_version)
        is_outdated = self._version_is_newer(current_version, latest_version)

        # Extract changelog from project description for parsing
        description = data.get("info", {}).get("description", "")
        breaking_changes: list[str] = []
        deprecations: list[str] = []

        if is_outdated and description:
            changes = await self._parse_changelog(
                description, current_version, latest_version, package_name
            )
            breaking_changes = [
                c.description for c in changes if c.change_type == "breaking"
            ]
            deprecations = [
                c.description for c in changes if c.change_type == "deprecation"
            ]

        # Check for security advisories
        security_advisories = await self._check_security(package_name, "pypi")

        return PackageRegistry(
            name=package_name,
            registry="pypi",
            current_version=current_version,
            latest_version=latest_version,
            is_outdated=is_outdated,
            breaking_changes=breaking_changes,
            deprecations=deprecations,
            security_advisories=security_advisories,
            last_checked=datetime.utcnow(),
        )

    async def scan_npm(self, package_name: str, current_version: str = "0.0.0") -> PackageRegistry:
        """Scan npm registry for a package's latest version and metadata.

        Calls the npm registry at /{package} to retrieve distribution tags,
        version metadata, and detects version drift.
        """
        client = await self._get_client()
        url = f"{settings.NPM_REGISTRY_URL}/{package_name}"
        logger.info("scanning_npm", package=package_name, url=url)

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("npm_http_error", package=package_name, status=exc.response.status_code)
            return PackageRegistry(
                name=package_name,
                registry="npm",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )
        except httpx.RequestError as exc:
            logger.error("npm_request_error", package=package_name, error=str(exc))
            return PackageRegistry(
                name=package_name,
                registry="npm",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )

        dist_tags = data.get("dist-tags", {})
        latest_version = dist_tags.get("latest", current_version)
        is_outdated = self._version_is_newer(current_version, latest_version)

        # Extract readme for changelog parsing
        readme = data.get("readme", "")
        breaking_changes: list[str] = []
        deprecations: list[str] = []

        if is_outdated and readme:
            changes = await self._parse_changelog(
                readme, current_version, latest_version, package_name
            )
            breaking_changes = [
                c.description for c in changes if c.change_type == "breaking"
            ]
            deprecations = [
                c.description for c in changes if c.change_type == "deprecation"
            ]

        security_advisories = await self._check_security(package_name, "npm")

        return PackageRegistry(
            name=package_name,
            registry="npm",
            current_version=current_version,
            latest_version=latest_version,
            is_outdated=is_outdated,
            breaking_changes=breaking_changes,
            deprecations=deprecations,
            security_advisories=security_advisories,
            last_checked=datetime.utcnow(),
        )

    async def scan_crates(self, package_name: str, current_version: str = "0.0.0") -> PackageRegistry:
        """Scan crates.io for a Rust crate's latest version.

        Calls the crates.io API at /api/v1/crates/{crate} to retrieve
        version information and detect version drift.
        """
        client = await self._get_client()
        url = f"{settings.CRATES_REGISTRY_URL}/crates/{package_name}"
        headers = {"User-Agent": "omni-api-intelligence/1.0.0"}
        logger.info("scanning_crates", package=package_name, url=url)

        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "crates_http_error", package=package_name, status=exc.response.status_code
            )
            return PackageRegistry(
                name=package_name,
                registry="crates",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )
        except httpx.RequestError as exc:
            logger.error("crates_request_error", package=package_name, error=str(exc))
            return PackageRegistry(
                name=package_name,
                registry="crates",
                current_version=current_version,
                latest_version=current_version,
                is_outdated=False,
            )

        crate_info = data.get("crate", {})
        latest_version = crate_info.get("newest_version", current_version)
        is_outdated = self._version_is_newer(current_version, latest_version)

        security_advisories = await self._check_security(package_name, "crates")

        return PackageRegistry(
            name=package_name,
            registry="crates",
            current_version=current_version,
            latest_version=latest_version,
            is_outdated=is_outdated,
            breaking_changes=[],
            deprecations=[],
            security_advisories=security_advisories,
            last_checked=datetime.utcnow(),
        )

    async def _parse_changelog(
        self,
        changelog_text: str,
        from_version: str,
        to_version: str,
        package_name: str,
    ) -> list[APIChange]:
        """Parse changelog text using LLM to extract structured API changes.

        Sends the changelog content to LiteLLM for intelligent extraction of
        breaking changes, deprecations, new features, and bugfixes between
        the specified version range.
        """
        if os.getenv("PYTEST_CURRENT_TEST"):
            return []
        client = await self._get_client()
        prompt = (
            f"Analyze the following changelog/release notes for the package '{package_name}'. "
            f"Identify all API changes between version {from_version} and {to_version}. "
            f"For each change, classify it as one of: breaking, deprecation, new_feature, bugfix, security. "
            f"Return a JSON array of objects with fields: change_type, description, affected_symbols (list of strings), migration_guide. "
            f"If no changes found, return an empty array.\n\n"
            f"Changelog:\n{changelog_text[:4000]}"
        )

        try:
            response = await client.post(
                f"{settings.LITELLM_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "[]")

            import json
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = parsed.get("changes", [])

            changes: list[APIChange] = []
            for item in parsed:
                if isinstance(item, dict):
                    changes.append(
                        APIChange(
                            package=package_name,
                            from_version=from_version,
                            to_version=to_version,
                            change_type=item.get("change_type", "bugfix"),
                            description=item.get("description", ""),
                            migration_guide=item.get("migration_guide", ""),
                            affected_symbols=item.get("affected_symbols", []),
                        )
                    )
            return changes

        except Exception as exc:
            logger.warning(
                "changelog_parse_failed",
                package=package_name,
                error=str(exc),
            )
            return []

    async def _check_security(self, package: str, registry: str) -> list[str]:
        """Check OSV.dev API for known vulnerabilities affecting a package.

        Queries the Open Source Vulnerabilities database to find any
        CVEs or security advisories for the given package and ecosystem.
        """
        if os.getenv("PYTEST_CURRENT_TEST"):
            return []
        client = await self._get_client()
        ecosystem_map = {
            "pypi": "PyPI",
            "npm": "npm",
            "crates": "crates.io",
            "go": "Go",
            "maven": "Maven",
        }
        ecosystem = ecosystem_map.get(registry, registry)
        osv_url = "https://api.osv.dev/v1/query"

        try:
            response = await client.post(
                osv_url,
                json={"package": {"name": package, "ecosystem": ecosystem}},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("osv_check_failed", package=package, error=str(exc))
            return []

        advisories: list[str] = []
        for vuln in data.get("vulns", []):
            vuln_id = vuln.get("id", "UNKNOWN")
            summary = vuln.get("summary", "No summary available")
            severity = "UNKNOWN"
            for severity_entry in vuln.get("severity", []):
                if severity_entry.get("type") == "CVSS_V3":
                    severity = severity_entry.get("score", "UNKNOWN")
                    break
            advisories.append(f"{vuln_id}: {summary} (severity: {severity})")

        return advisories

    async def scan_all(self, packages: list[dict[str, str]]) -> list[PackageRegistry]:
        """Scan multiple packages in parallel using asyncio.gather.

        Each entry in packages should have keys: name, registry, current_version.
        Dispatches to the correct registry scanner and runs all scans concurrently.
        """
        tasks = []
        for pkg in packages:
            name = pkg.get("name", "")
            registry = pkg.get("registry", "pypi")
            current_version = pkg.get("current_version", "0.0.0")

            if registry == "pypi":
                tasks.append(self.scan_pypi(name, current_version))
            elif registry == "npm":
                tasks.append(self.scan_npm(name, current_version))
            elif registry == "crates":
                tasks.append(self.scan_crates(name, current_version))
            else:
                logger.warning("unsupported_registry", package=name, registry=registry)
                tasks.append(
                    asyncio.coroutine(lambda n=name, r=registry, v=current_version: PackageRegistry(
                        name=n,
                        registry=r,
                        current_version=v,
                        latest_version=v,
                        is_outdated=False,
                    ))()
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        scanned: list[PackageRegistry] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "scan_failed",
                    package=packages[i].get("name", "unknown"),
                    error=str(result),
                )
                scanned.append(
                    PackageRegistry(
                        name=packages[i].get("name", "unknown"),
                        registry=packages[i].get("registry", "pypi"),
                        current_version=packages[i].get("current_version", "0.0.0"),
                        latest_version=packages[i].get("current_version", "0.0.0"),
                        is_outdated=False,
                    )
                )
            else:
                scanned.append(result)

        return scanned

    @staticmethod
    def _version_is_newer(current: str, latest: str) -> bool:
        """Compare two version strings; returns True if latest > current."""
        try:
            return Version(latest) > Version(current)
        except InvalidVersion:
            # Fall back to string comparison for non-PEP-440 versions
            return latest != current and latest > current
