from __future__ import annotations

from fastapi import APIRouter

from src.services.contract_tracker import ContractTracker
from src.services.graph_builder import ServiceGraphBuilder

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/graph")
def graph(root: str = "services"):
    return ServiceGraphBuilder().build_graph(root)


@router.get("/graph/{service}")
def one(service: str, root: str = "services"):
    g = ServiceGraphBuilder().build_graph(root)
    deps = [dst for src, dst in g.edges if src == service]
    consumers = [src for src, dst in g.edges if dst == service]
    return {"service": service, "depends_on": deps, "consumed_by": consumers}


@router.get("/contracts/{service}")
def contracts(service: str, root: str = "services"):
    return ContractTracker().extract_contracts(f"{root}/{service}")
