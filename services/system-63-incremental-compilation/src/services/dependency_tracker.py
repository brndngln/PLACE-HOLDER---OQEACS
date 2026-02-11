from __future__ import annotations

from pathlib import Path

from src.models import DependencyGraph


class DependencyTracker:
    def build_dep_graph(self, project_path: str) -> DependencyGraph:
        root = Path(project_path)
        nodes: list[str] = []
        edges: list[tuple[str, str]] = []
        for pyf in root.rglob("*.py"):
            rel = str(pyf.relative_to(root))
            nodes.append(rel)
            text = pyf.read_text(errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("from "):
                    dep = line.split()[1].replace(".", "/") + ".py"
                    edges.append((rel, dep))
        return DependencyGraph(nodes=sorted(set(nodes)), edges=sorted(set(edges)))
