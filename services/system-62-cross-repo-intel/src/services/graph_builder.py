from __future__ import annotations

from pathlib import Path

from src.models import ServiceGraph


class ServiceGraphBuilder:
    def build_graph(self, services_dir: str) -> ServiceGraph:
        root = Path(services_dir)
        nodes: set[str] = set()
        edges: set[tuple[str, str]] = set()

        for compose in root.rglob("docker-compose.yml"):
            service_name = compose.parent.name
            nodes.add(service_name)
            text = compose.read_text(errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.endswith(":") and line.startswith("omni-"):
                    dep = line.rstrip(":").replace("omni-", "")
                    nodes.add(dep)
                    edges.add((service_name, dep))

        sorted_nodes = sorted(nodes)
        sorted_edges = sorted(edges)
        return ServiceGraph(
            nodes=sorted_nodes,
            edges=sorted_edges,
            total_services=len(sorted_nodes),
            total_relationships=len(sorted_edges),
        )
