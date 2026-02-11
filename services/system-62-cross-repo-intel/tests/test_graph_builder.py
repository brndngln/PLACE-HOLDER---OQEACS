from __future__ import annotations

from src.services.graph_builder import ServiceGraphBuilder


def test_build_graph_from_empty(tmp_path) -> None:
    g = ServiceGraphBuilder().build_graph(str(tmp_path))
    assert g.total_services == 0


def test_build_graph_detects_service(tmp_path) -> None:
    svc = tmp_path / "svc"
    svc.mkdir()
    (svc / "docker-compose.yml").write_text("services:\n  app:\n    image: x\n", encoding="utf-8")
    g = ServiceGraphBuilder().build_graph(str(tmp_path))
    assert "svc" in g.nodes


def test_edges_list_type(tmp_path) -> None:
    g = ServiceGraphBuilder().build_graph(str(tmp_path))
    assert isinstance(g.edges, list)


def test_totals_consistent(tmp_path) -> None:
    g = ServiceGraphBuilder().build_graph(str(tmp_path))
    assert g.total_relationships == len(g.edges)
