from __future__ import annotations

from fastapi import APIRouter

from src.models import SBOMDocument, ScanResult
from src.routers.scan import _store
from src.services.sbom_generator import SBOMGenerator

router = APIRouter(prefix="/api/v1", tags=["sbom"])


@router.post("/sbom/generate", response_model=SBOMDocument)
def generate(scan: ScanResult) -> SBOMDocument:
    return SBOMGenerator().generate_sbom(scan.tree)


@router.get("/licenses/{scan_id}")
def licenses(scan_id: str):
    item = _store.get(scan_id)
    return item.licenses if item else []
