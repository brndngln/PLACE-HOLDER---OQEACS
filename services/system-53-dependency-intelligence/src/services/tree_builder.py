from __future__ import annotations

import json
import uuid
from pathlib import Path

import networkx as nx

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
        g = nx.DiGraph()
        for node in nodes:
            g.add_node(node.name)
        has_cycles = not nx.is_directed_acyclic_graph(g)
        return DependencyTree(id=str(uuid.uuid4()), nodes=nodes, edges=edges, has_cycles=has_cycles)

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
