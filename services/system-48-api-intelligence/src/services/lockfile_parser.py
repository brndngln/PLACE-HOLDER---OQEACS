"""Lockfile parser: extracts (name, version) tuples from various lockfile formats."""

from __future__ import annotations

import json
import re

import structlog

logger = structlog.get_logger(__name__)


class LockfileParser:
    """Parses lockfiles from Python, Node.js, Rust, and Go ecosystems."""

    def parse_requirements_txt(self, content: str) -> list[tuple[str, str]]:
        """Parse a requirements.txt file content into (name, version) tuples.

        Handles pinned versions (==), comments, blank lines, extras, and
        environment markers. Packages without pinned versions are included
        with version "unpinned".
        """
        packages: list[tuple[str, str]] = []

        for raw_line in content.splitlines():
            line = raw_line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Remove inline comments
            if " #" in line:
                line = line[: line.index(" #")].strip()

            # Remove environment markers
            if ";" in line:
                line = line[: line.index(";")].strip()

            # Remove extras like package[extra1,extra2]
            if "[" in line:
                bracket_start = line.index("[")
                bracket_end = line.index("]") if "]" in line else len(line)
                line = line[:bracket_start] + line[bracket_end + 1:]
                line = line.strip()

            # Parse pinned versions: name==version
            if "==" in line:
                parts = line.split("==", 1)
                name = parts[0].strip().lower()
                version = parts[1].strip()
                packages.append((name, version))
            elif ">=" in line:
                parts = line.split(">=", 1)
                name = parts[0].strip().lower()
                version_part = parts[1].strip()
                # Handle >=1.0,<2.0 style constraints
                if "," in version_part:
                    version_part = version_part.split(",")[0].strip()
                packages.append((name, version_part))
            elif "~=" in line:
                parts = line.split("~=", 1)
                name = parts[0].strip().lower()
                version = parts[1].strip()
                packages.append((name, version))
            elif line and not any(op in line for op in ["<", ">", "!", "~"]):
                # Bare package name without version
                packages.append((line.lower(), "unpinned"))

        logger.info("parsed_requirements_txt", count=len(packages))
        return packages

    def parse_package_lock(self, content: str) -> list[tuple[str, str]]:
        """Parse a package-lock.json file content into (name, version) tuples.

        Handles both npm lockfile v2/v3 format (with 'packages' field) and
        v1 format (with 'dependencies' field). Extracts the direct and
        transitive dependencies.
        """
        packages: list[tuple[str, str]] = []

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("package_lock_parse_error", error=str(exc))
            return packages

        # npm lockfile v2/v3 format
        if "packages" in data:
            for pkg_path, pkg_info in data["packages"].items():
                if not pkg_path:
                    continue  # Skip the root package
                # Extract name from path like "node_modules/package-name"
                name = pkg_path.split("node_modules/")[-1] if "node_modules/" in pkg_path else pkg_path
                version = pkg_info.get("version", "unknown")
                if name and version:
                    packages.append((name, version))

        # npm lockfile v1 format (fallback)
        elif "dependencies" in data:
            self._parse_npm_deps_recursive(data["dependencies"], packages)

        logger.info("parsed_package_lock", count=len(packages))
        return packages

    def _parse_npm_deps_recursive(
        self,
        deps: dict,
        packages: list[tuple[str, str]],
    ) -> None:
        """Recursively parse npm v1 dependencies (handles nested deps)."""
        for name, info in deps.items():
            version = info.get("version", "unknown")
            packages.append((name, version))
            # Recurse into nested dependencies
            if "dependencies" in info:
                self._parse_npm_deps_recursive(info["dependencies"], packages)

    def parse_cargo_lock(self, content: str) -> list[tuple[str, str]]:
        """Parse a Cargo.lock file content into (name, version) tuples.

        Handles TOML-format Cargo.lock files by extracting each [[package]]
        section's name and version fields.
        """
        packages: list[tuple[str, str]] = []
        current_name: str | None = None
        current_version: str | None = None
        in_package = False

        for line in content.splitlines():
            stripped = line.strip()

            if stripped == "[[package]]":
                # Save the previous package if complete
                if current_name and current_version:
                    packages.append((current_name, current_version))
                current_name = None
                current_version = None
                in_package = True
                continue

            if in_package:
                name_match = re.match(r'^name\s*=\s*"(.+)"$', stripped)
                if name_match:
                    current_name = name_match.group(1).lower()
                    continue

                version_match = re.match(r'^version\s*=\s*"(.+)"$', stripped)
                if version_match:
                    current_version = version_match.group(1)
                    continue

                # End of package block (empty line or new section)
                if stripped == "" or stripped.startswith("["):
                    if current_name and current_version:
                        packages.append((current_name, current_version))
                        current_name = None
                        current_version = None
                    if stripped.startswith("[") and stripped != "[[package]]":
                        in_package = False

        # Don't forget the last package
        if current_name and current_version:
            packages.append((current_name, current_version))

        logger.info("parsed_cargo_lock", count=len(packages))
        return packages

    def parse_go_sum(self, content: str) -> list[tuple[str, str]]:
        """Parse a go.sum file content into (name, version) tuples.

        Each line in go.sum has the format:
            module version hash
        where version may have /go.mod suffix. Deduplicates entries since
        go.sum often has both a module entry and a go.mod entry per dependency.
        """
        packages: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            parts = stripped.split()
            if len(parts) < 3:
                continue

            module = parts[0]
            version_raw = parts[1]

            # Remove /go.mod suffix if present
            version = version_raw.replace("/go.mod", "")

            # Remove the 'v' prefix common in Go semver
            if version.startswith("v"):
                version = version[1:]

            # Remove +incompatible suffix
            version = version.replace("+incompatible", "")

            key = (module.lower(), version)
            if key not in seen:
                seen.add(key)
                packages.append((module.lower(), version))

        logger.info("parsed_go_sum", count=len(packages))
        return packages
