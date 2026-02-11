from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.models import ScanRequest, ScanResult
from src.services.license_checker import LicenseChecker
from src.services.tree_builder import DependencyTreeBuilder
from src.services.vulnerability_scanner import VulnerabilityScanner

router = APIRouter(prefix="/api/v1", tags=["scan"])
_store: dict[str, ScanResult] = {}


@router.post("/scan", response_model=ScanResult)
async def scan(req: ScanRequest) -> ScanResult:
    tree = DependencyTreeBuilder().build_tree(req.lockfile_path)
    vulns = await VulnerabilityScanner().scan_vulnerabilities(tree)
    licenses = LicenseChecker().check_licenses(tree)
    result = ScanResult(tree=tree, vulnerabilities=vulns, licenses=licenses)
    _store[tree.id] = result
    return result


@router.get("/tree/{scan_id}", response_model=ScanResult)
def get_tree(scan_id: str) -> ScanResult:
    if scan_id not in _store:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _store[scan_id]


@router.get("/vulnerabilities/{scan_id}")
def get_vulns(scan_id: str):
    if scan_id not in _store:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _store[scan_id].vulnerabilities
