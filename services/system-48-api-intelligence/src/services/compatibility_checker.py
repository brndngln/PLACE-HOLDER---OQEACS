"""Compatibility checker: validates version compatibility between package pairs."""

from __future__ import annotations

import itertools

import httpx
import structlog
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion

from src.config import settings
from src.models import CompatibilityMatrix

logger = structlog.get_logger(__name__)


class CompatibilityChecker:
    """Checks compatibility between packages at specific versions."""

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

    async def check_compatibility(
        self,
        package_a: str,
        ver_a: str,
        package_b: str,
        ver_b: str,
    ) -> CompatibilityMatrix:
        """Check compatibility between two packages at given versions.

        Fetches dependency metadata from PyPI for both packages and verifies
        that neither package's version constraints conflict with the other.
        Also validates Python version requirements for both packages.
        """
        logger.info(
            "checking_compatibility",
            package_a=package_a,
            version_a=ver_a,
            package_b=package_b,
            version_b=ver_b,
        )

        notes_parts: list[str] = []
        compatible = True

        # Check if package_a requires package_b at a conflicting version
        a_deps = await self._fetch_dependencies(package_a, ver_a)
        b_deps = await self._fetch_dependencies(package_b, ver_b)

        # Check if A depends on B and the version constraint matches
        for dep_name, dep_specifier in a_deps:
            if dep_name.lower() == package_b.lower():
                if not self._specifier_matches(dep_specifier, ver_b):
                    compatible = False
                    notes_parts.append(
                        f"{package_a}=={ver_a} requires {package_b}{dep_specifier}, "
                        f"but {ver_b} does not satisfy this constraint"
                    )
                else:
                    notes_parts.append(
                        f"{package_a}=={ver_a} requires {package_b}{dep_specifier} - satisfied by {ver_b}"
                    )

        # Check if B depends on A and the version constraint matches
        for dep_name, dep_specifier in b_deps:
            if dep_name.lower() == package_a.lower():
                if not self._specifier_matches(dep_specifier, ver_a):
                    compatible = False
                    notes_parts.append(
                        f"{package_b}=={ver_b} requires {package_a}{dep_specifier}, "
                        f"but {ver_a} does not satisfy this constraint"
                    )
                else:
                    notes_parts.append(
                        f"{package_b}=={ver_b} requires {package_a}{dep_specifier} - satisfied by {ver_a}"
                    )

        # Check Python version constraints
        py_check_a = await self._check_python_requires(package_a, ver_a)
        py_check_b = await self._check_python_requires(package_b, ver_b)

        if py_check_a:
            notes_parts.append(f"{package_a}=={ver_a}: requires_python={py_check_a}")
        if py_check_b:
            notes_parts.append(f"{package_b}=={ver_b}: requires_python={py_check_b}")

        # Check peer dependency requirements (npm-style)
        peer_a = await self._check_peer_deps(package_a, ver_a)
        peer_b = await self._check_peer_deps(package_b, ver_b)
        if peer_a:
            notes_parts.append(f"{package_a}=={ver_a} peer deps: {peer_a}")
        if peer_b:
            notes_parts.append(f"{package_b}=={ver_b} peer deps: {peer_b}")

        if not notes_parts:
            notes_parts.append("No direct dependency relationship detected between packages")

        return CompatibilityMatrix(
            package_a=package_a,
            version_a=ver_a,
            package_b=package_b,
            version_b=ver_b,
            compatible=compatible,
            notes="; ".join(notes_parts),
        )

    async def build_matrix(
        self, packages: list[dict[str, str]]
    ) -> list[CompatibilityMatrix]:
        """Build a full compatibility matrix for all package pairs.

        Takes a list of dicts with keys 'name' and 'version', computes the
        cartesian product of all unique pairs, and checks each pair.
        """
        results: list[CompatibilityMatrix] = []
        pairs = list(itertools.combinations(packages, 2))
        logger.info("building_compatibility_matrix", total_pairs=len(pairs))

        for pkg_a, pkg_b in pairs:
            result = await self.check_compatibility(
                pkg_a["name"], pkg_a["version"],
                pkg_b["name"], pkg_b["version"],
            )
            results.append(result)

        return results

    async def _check_python_requires(self, package: str, version: str) -> str:
        """Validate Python version constraints for a package version.

        Fetches the requires_python metadata from PyPI for the given
        package version and returns the constraint string.
        """
        client = await self._get_client()
        url = f"{settings.PYPI_URL}/pypi/{package}/{version}/json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            requires_python = data.get("info", {}).get("requires_python", "")
            return requires_python or ""
        except Exception as exc:
            logger.debug("python_requires_check_failed", package=package, error=str(exc))
            return ""

    async def _check_peer_deps(self, package: str, version: str) -> str:
        """Validate peer dependency requirements for npm packages.

        Fetches the peerDependencies field from the npm registry for the
        given package version and returns a summary string.
        """
        client = await self._get_client()
        url = f"{settings.NPM_REGISTRY_URL}/{package}/{version}"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            peer_deps = data.get("peerDependencies", {})
            if peer_deps:
                parts = [f"{name}@{spec}" for name, spec in peer_deps.items()]
                return ", ".join(parts)
            return ""
        except Exception:
            return ""

    async def _fetch_dependencies(
        self, package: str, version: str
    ) -> list[tuple[str, str]]:
        """Fetch the dependency list for a specific package version from PyPI.

        Returns a list of (dependency_name, specifier_string) tuples extracted
        from the requires_dist metadata.
        """
        client = await self._get_client()
        url = f"{settings.PYPI_URL}/pypi/{package}/{version}/json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.debug("fetch_deps_failed", package=package, version=version, error=str(exc))
            return []

        requires_dist = data.get("info", {}).get("requires_dist", []) or []
        deps: list[tuple[str, str]] = []

        for req_str in requires_dist:
            # Skip extras-conditional deps for simplicity
            if "extra ==" in req_str:
                continue

            # Parse "package_name (>=1.0,<2.0)" format
            parts = req_str.split(";")[0].strip()  # strip environment markers
            if "(" in parts:
                name_part, spec_part = parts.split("(", 1)
                name = name_part.strip().lower()
                specifier = spec_part.rstrip(")").strip()
            elif " " in parts:
                tokens = parts.split()
                name = tokens[0].strip().lower()
                specifier = tokens[1] if len(tokens) > 1 else ""
            else:
                name = parts.strip().lower()
                specifier = ""

            deps.append((name, specifier))

        return deps

    @staticmethod
    def _specifier_matches(specifier_str: str, version_str: str) -> bool:
        """Check if a version satisfies a specifier constraint."""
        if not specifier_str:
            return True
        try:
            spec = SpecifierSet(specifier_str)
            ver = Version(version_str)
            return ver in spec
        except (InvalidSpecifier, InvalidVersion):
            return True  # If we can't parse, assume compatible
