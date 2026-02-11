from __future__ import annotations

from pathlib import Path

import networkx as nx

from src.models import ServiceGraph


class ServiceGraphBuilder:
    def build_graph(self, services_dir: str) -> ServiceGraph:
        root = Path(services_dir)
        graph = nx.DiGraph()

        for compose in root.rglob("docker-compose.yml"):
            service_name = compose.parent.name
            graph.add_node(service_name)
            text = compose.read_text(errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.endswith(":") and line.startswith("omni-"):
                    dep = line.rstrip(":").replace("omni-", "")
                    graph.add_edge(service_name, dep)

        nodes = sorted(graph.nodes())
        edges = sorted((a, b) for a, b in graph.edges())
        return ServiceGraph(nodes=nodes, edges=edges, total_services=len(nodes), total_relationships=len(edges))
