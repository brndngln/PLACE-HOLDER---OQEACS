"""Upgrade planner: topological sort of upgrades with risk assessment."""

from __future__ import annotations

import httpx
import structlog
from packaging.version import Version, InvalidVersion

from src.config import settings
from src.models import APIChange, PackageRegistry, ScanResult, UpgradePlan

logger = structlog.get_logger(__name__)


class UpgradePlanner:
    """Plans safe upgrade paths with risk assessment and migration guides."""

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

    async def plan_upgrades(self, scan_result: ScanResult) -> list[UpgradePlan]:
        """Generate an ordered upgrade plan from a scan result.

        Performs topological sorting of packages based on their interdependencies
        so that foundational packages are upgraded first. Each package receives
        a risk assessment and migration steps.
        """
        outdated = [pkg for pkg in scan_result.packages if pkg.is_outdated]
        if not outdated:
            logger.info("no_upgrades_needed")
            return []

        logger.info("planning_upgrades", outdated_count=len(outdated))

        # Build a dependency graph for topological sorting
        dep_graph: dict[str, set[str]] = {}
        for pkg in outdated:
            dep_graph[pkg.name] = set()
            cascade = await self._find_cascade_upgrades(pkg.name, pkg.latest_version)
            for dep_name in cascade:
                if any(p.name == dep_name for p in outdated):
                    dep_graph[pkg.name].add(dep_name)

        # Topological sort using Kahn's algorithm
        sorted_names = self._topological_sort(dep_graph)

        # Build upgrade plans in sorted order
        plans: list[UpgradePlan] = []
        for name in sorted_names:
            pkg = next((p for p in outdated if p.name == name), None)
            if pkg is None:
                continue

            changes = [
                APIChange(
                    package=pkg.name,
                    from_version=pkg.current_version,
                    to_version=pkg.latest_version,
                    change_type="breaking",
                    description=bc,
                )
                for bc in pkg.breaking_changes
            ]

            risk = self._calculate_risk(
                pkg.name, pkg.current_version, pkg.latest_version, changes
            )
            cascade = await self._find_cascade_upgrades(pkg.name, pkg.latest_version)
            migration_steps = await self._generate_migration_steps(changes)

            plans.append(
                UpgradePlan(
                    package=pkg.name,
                    from_v=pkg.current_version,
                    to_v=pkg.latest_version,
                    risk=risk,
                    also_upgrade=cascade,
                    migration_steps=migration_steps,
                )
            )

        return plans

    def _calculate_risk(
        self,
        package: str,
        from_v: str,
        to_v: str,
        changes: list[APIChange],
    ) -> str:
        """Calculate risk level for upgrading a package.

        Uses a heuristic based on:
        - Major version bumps = high risk
        - Number of breaking changes
        - Presence of security advisories (forces critical)
        - Deprecation count
        """
        # Check for major version bump
        try:
            from_ver = Version(from_v)
            to_ver = Version(to_v)
            major_bump = to_ver.major > from_ver.major
            minor_bump = to_ver.minor > from_ver.minor
        except InvalidVersion:
            major_bump = False
            minor_bump = False

        breaking_count = sum(1 for c in changes if c.change_type == "breaking")
        security_count = sum(1 for c in changes if c.change_type == "security")

        if security_count > 0:
            return "critical"
        if major_bump and breaking_count > 3:
            return "critical"
        if major_bump or breaking_count > 1:
            return "high"
        if minor_bump or breaking_count == 1:
            return "medium"
        return "low"

    async def _find_cascade_upgrades(
        self, package: str, to_version: str
    ) -> list[str]:
        """Find packages that also need upgrading when upgrading a target package.

        Checks the target version's dependencies against the current environment
        to identify any packages that would need simultaneous upgrades.
        """
        client = await self._get_client()
        url = f"{settings.PYPI_URL}/pypi/{package}/{to_version}/json"

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.debug("cascade_check_failed", package=package, error=str(exc))
            return []

        requires_dist = data.get("info", {}).get("requires_dist", []) or []
        cascade_packages: list[str] = []

        for req_str in requires_dist:
            if "extra ==" in req_str:
                continue
            parts = req_str.split(";")[0].strip()
            if "(" in parts:
                name = parts.split("(")[0].strip().lower()
            elif " " in parts:
                name = parts.split()[0].strip().lower()
            else:
                name = parts.strip().lower()

            if name and name != package.lower():
                cascade_packages.append(name)

        return cascade_packages

    async def _generate_migration_steps(
        self, changes: list[APIChange]
    ) -> list[str]:
        """Generate step-by-step migration instructions using the LLM.

        For each breaking change or deprecation, produces concrete code
        migration steps. Falls back to basic instructions if LLM is unavailable.
        """
        if not changes:
            return ["No breaking changes detected. Safe to upgrade directly."]

        breaking = [c for c in changes if c.change_type in ("breaking", "deprecation")]
        if not breaking:
            return ["No breaking changes detected. Safe to upgrade directly."]

        # Attempt LLM-powered migration guide generation
        client = await self._get_client()
        change_descriptions = "\n".join(
            f"- [{c.change_type}] {c.description}" for c in breaking
        )
        prompt = (
            f"Generate a concise step-by-step migration guide for the following API changes "
            f"in package '{changes[0].package}' from version {changes[0].from_version} "
            f"to {changes[0].to_version}:\n\n{change_descriptions}\n\n"
            f"Return a JSON array of strings, each string being one migration step. "
            f"Be specific about code changes needed."
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
                parsed = parsed.get("steps", parsed.get("migration_steps", []))
            if isinstance(parsed, list):
                return [str(step) for step in parsed]

        except Exception as exc:
            logger.warning("migration_steps_llm_failed", error=str(exc))

        # Fallback: generate basic migration steps from change metadata
        steps: list[str] = []
        steps.append(f"1. Review all {len(breaking)} breaking changes before upgrading")
        for i, change in enumerate(breaking, start=2):
            if change.migration_guide:
                steps.append(f"{i}. {change.migration_guide}")
            else:
                steps.append(f"{i}. Address: {change.description}")
            if change.affected_symbols:
                symbols = ", ".join(change.affected_symbols)
                steps.append(f"   Affected symbols: {symbols}")
        steps.append(f"{len(steps) + 1}. Run full test suite after upgrading")
        steps.append(f"{len(steps) + 1}. Monitor application logs for deprecation warnings")

        return steps

    @staticmethod
    def _topological_sort(graph: dict[str, set[str]]) -> list[str]:
        """Kahn's algorithm for topological sorting of the dependency graph.

        Returns packages sorted so that dependencies come before dependents,
        ensuring safe upgrade order.
        """
        # Calculate in-degree for each node
        in_degree: dict[str, int] = {node: 0 for node in graph}
        for node, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0)
                else:
                    in_degree[dep] = 0

        # Recount: edges go from node -> dep means dep should come first
        in_degree = {node: 0 for node in graph}
        for node, deps in graph.items():
            for dep in deps:
                if dep not in in_degree:
                    in_degree[dep] = 0

        for node, deps in graph.items():
            for dep in deps:
                if node in in_degree:
                    in_degree[node] = in_degree.get(node, 0) + 1

        # Start with nodes that have no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        queue.sort()  # deterministic ordering
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            # For each node that depends on this one, decrement in-degree
            for other, deps in graph.items():
                if node in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)
            queue.sort()

        # Add any remaining nodes (cycles)
        for node in graph:
            if node not in result:
                result.append(node)

        return result
