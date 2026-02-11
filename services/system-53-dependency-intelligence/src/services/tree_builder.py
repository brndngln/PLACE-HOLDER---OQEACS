from __future__ import annotations

import json
import uuid
from pathlib import Path

from src.models import DependencyNode, DependencyTree


class DependencyTreeBuilder:
    def build_tree(self, lockfile_path: str) -> DependencyTree:
        path = Path(lockfile_path)
        if not path.exists():
            return DependencyTree(id=str(uuid.uuid4()), nodes=[], edges=[], has_cycles=False)
        if path.name == "requirements.txt":
            parsed = self._parse_requirements(path.read_text(encoding="utf-8", errors="ignore"))
        elif path.name == "package-lock.json":
            parsed = self._parse_package_lock(path.read_text(encoding="utf-8", errors="ignore"))
        elif path.name == "Cargo.lock":
            parsed = self._parse_cargo(path.read_text(encoding="utf-8", errors="ignore"))
        else:
            parsed = []

        nodes = [DependencyNode(name=n, version=v, ecosystem=self._ecosystem(path.name), direct=True) for n, v in parsed]
        edges: list[tuple[str, str]] = []
        has_cycles = self._has_cycles(nodes, edges)
        return DependencyTree(id=str(uuid.uuid4()), nodes=nodes, edges=edges, has_cycles=has_cycles)

    @staticmethod
    def _has_cycles(nodes: list[DependencyNode], edges: list[tuple[str, str]]) -> bool:
        graph: dict[str, list[str]] = {node.name: [] for node in nodes}
        for source, target in edges:
            graph.setdefault(source, []).append(target)

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(name: str) -> bool:
            if name in visiting:
                return True
            if name in visited:
                return False
            visiting.add(name)
            for nxt in graph.get(name, []):
                if dfs(nxt):
                    return True
            visiting.remove(name)
            visited.add(name)
            return False

        return any(dfs(node.name) for node in nodes)

    @staticmethod
    def _ecosystem(lockfile: str) -> str:
        if lockfile == "requirements.txt":
            return "pypi"
        if lockfile == "package-lock.json":
            return "npm"
        if lockfile == "Cargo.lock":
            return "crates"
        return "unknown"

    @staticmethod
    def _parse_requirements(content: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                n, v = line.split("==", 1)
                out.append((n.strip(), v.strip()))
        return out

    @staticmethod
    def _parse_package_lock(content: str) -> list[tuple[str, str]]:
        data = json.loads(content or "{}")
        out: list[tuple[str, str]] = []
        for key, meta in (data.get("packages") or {}).items():
            if key.startswith("node_modules/") and isinstance(meta, dict):
                out.append((key.split("node_modules/", 1)[1], str(meta.get("version", "0.0.0"))))
        return out

    @staticmethod
    def _parse_cargo(content: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        current = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("name ="):
                current["name"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("version ="):
                current["version"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("[[package]]") and current:
                if "name" in current and "version" in current:
                    out.append((current["name"], current["version"]))
                current = {}
        if "name" in current and "version" in current:
            out.append((current["name"], current["version"]))
        return out
