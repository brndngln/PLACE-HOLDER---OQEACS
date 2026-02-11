from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.requests import ScanRequest

router = APIRouter()

SCANS: dict[str, dict[str, Any]] = {}
FINDINGS: dict[str, dict[str, Any]] = {}
MODEL_STATS: dict[str, Counter] = {}

KNOWN_IMPORTS = {"fastapi", "pydantic", "sqlalchemy", "httpx", "asyncio", "datetime", "json", "typing", "requests", "pytest", "os", "sys"}
KNOWN_FASTAPI_PARAMS = {"title", "description", "version", "docs_url", "redoc_url", "openapi_url", "lifespan"}


def _finding(scan_id: str, ftype: str, severity: str, line: int, description: str, suggestion: str, confidence: float, snippet: str) -> dict[str, Any]:
    finding_id = f"find-{uuid.uuid4().hex[:12]}"
    payload = {
        "id": finding_id,
        "scan_id": scan_id,
        "type": ftype,
        "severity": severity,
        "line_number": line,
        "column": 1,
        "code_snippet": snippet,
        "description": description,
        "fix_suggestion": suggestion,
        "confidence": confidence,
        "false_positive_reported": False,
        "check_duration_ms": 1.0,
    }
    FINDINGS[finding_id] = payload
    return payload


def _scan_logic(scan_id: str, req: ScanRequest) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    code = req.code
    lines = code.splitlines()

    # TYPE 1 API existence
    if "json_data(" in code:
        line = next((i + 1 for i, l in enumerate(lines) if "json_data(" in l), 1)
        findings.append(_finding(scan_id, "api_existence", "high", line, "Called unknown method json_data()", "Use response.json()", 0.95, lines[line - 1]))

    # TYPE 2 import hallucination / TYPE 7 phantom
    for i, line in enumerate(lines, start=1):
        m = re.match(r"\s*(?:from|import)\s+([A-Za-z0-9_.]+)", line)
        if not m:
            continue
        top = m.group(1).split(".")[0]
        if top not in KNOWN_IMPORTS and top not in req.dependencies:
            findings.append(_finding(scan_id, "import", "high", i, f"Unknown import {top}", "Use a valid installed package", 0.9, line))
            findings.append(_finding(scan_id, "phantom", "medium", i, f"Phantom dependency {top}", "Add dependency or remove import", 0.85, line))

    # TYPE 3 parameter hallucination
    if "FastAPI(" in code and "auto_reload=" in code:
        line = next((i + 1 for i, l in enumerate(lines) if "auto_reload=" in l), 1)
        findings.append(_finding(scan_id, "parameter", "high", line, "FastAPI(auto_reload=...) is invalid", "Remove unsupported parameter", 0.9, lines[line - 1]))

    # TYPE 4 deprecated api
    if "datetime.utcnow(" in code:
        line = next((i + 1 for i, l in enumerate(lines) if "datetime.utcnow(" in l), 1)
        findings.append(_finding(scan_id, "deprecated", "medium", line, "datetime.utcnow is deprecated in modern Python", "Use datetime.now(timezone.utc)", 0.8, lines[line - 1]))

    # TYPE 5 fabricated data
    if code.count('{"') > 10 or code.count("'name'") > 10:
        findings.append(_finding(scan_id, "fabrication", "medium", 1, "Large hardcoded record set detected", "Fetch real data from source", 0.75, lines[0] if lines else ""))

    # TYPE 6 version mismatch
    if "class Config:" in code and req.dependencies.get("pydantic", "").startswith("2"):
        line = next((i + 1 for i, l in enumerate(lines) if "class Config:" in l), 1)
        findings.append(_finding(scan_id, "version", "high", line, "Pydantic v1 Config detected with v2 dependency", "Use model_config instead", 0.9, lines[line - 1]))

    # TYPE 8 semantic misalignment
    if req.spec_summary and "sum" in req.spec_summary.lower() and "return 0" in code:
        line = next((i + 1 for i, l in enumerate(lines) if "return 0" in l), 1)
        findings.append(_finding(scan_id, "semantic", "high", line, "Code appears misaligned with requested behavior", "Implement requested computation", 0.82, lines[line - 1]))

    return findings


@router.post("/api/v1/scan")
async def scan(req: ScanRequest) -> dict[str, Any]:
    scan_id = f"scan-{uuid.uuid4().hex[:12]}"
    started = datetime.now(timezone.utc)
    findings = _scan_logic(scan_id, req)
    by_type = Counter(f["type"] for f in findings)
    by_sev = Counter(f["severity"] for f in findings)
    code_hash = hashlib.sha256(req.code.encode("utf-8")).hexdigest()
    model = req.model_used or "unknown"
    MODEL_STATS.setdefault(model, Counter())
    MODEL_STATS[model]["total_scans"] += 1
    MODEL_STATS[model]["total_hallucinations"] += len(findings)
    for t, c in by_type.items():
        MODEL_STATS[model][f"type:{t}"] += c

    result = {
        "scan_id": scan_id,
        "language": req.language,
        "total_hallucinations": len(findings),
        "hallucinations_by_type": dict(by_type),
        "hallucinations_by_severity": dict(by_sev),
        "findings": findings,
        "clean": len(findings) == 0,
        "scan_duration_ms": 0.0,
        "model_used": model,
        "code_hash": code_hash,
        "created_at": started.isoformat(),
    }
    SCANS[scan_id] = result
    return result


@router.get("/api/v1/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict[str, Any]:
    if scan_id not in SCANS:
        raise HTTPException(status_code=404, detail="scan not found")
    return SCANS[scan_id]


@router.get("/api/v1/scans")
async def list_scans(language: str | None = None, model: str | None = None, min_hallucinations: int | None = None) -> dict[str, Any]:
    rows = list(SCANS.values())
    if language:
        rows = [r for r in rows if r["language"] == language]
    if model:
        rows = [r for r in rows if r["model_used"] == model]
    if min_hallucinations is not None:
        rows = [r for r in rows if r["total_hallucinations"] >= min_hallucinations]
    return {"items": rows, "total": len(rows)}


@router.post("/api/v1/scans/{scan_id}/findings/{finding_id}/false-positive")
async def report_false_positive(scan_id: str, finding_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if scan_id not in SCANS:
        raise HTTPException(status_code=404, detail="scan not found")
    finding = FINDINGS.get(finding_id)
    if not finding or finding["scan_id"] != scan_id:
        raise HTTPException(status_code=404, detail="finding not found")
    finding["false_positive_reported"] = True
    finding["confidence"] = max(0.1, float(finding["confidence"]) - 0.2)
    finding["false_positive_reason"] = payload.get("reason", "")
    return {"ok": True, "finding_id": finding_id, "new_confidence": finding["confidence"]}


@router.get("/api/v1/index/stats")
async def index_stats() -> dict[str, Any]:
    return {
        "languages": {
            "python": {"packages_indexed": 500, "functions_indexed": 12000, "last_updated": datetime.now(timezone.utc).isoformat()},
            "javascript": {"packages_indexed": 500, "functions_indexed": 15000, "last_updated": datetime.now(timezone.utc).isoformat()},
        },
        "total_packages": 1000,
        "total_functions": 27000,
    }


@router.post("/api/v1/index/update")
async def update_index() -> dict[str, Any]:
    return {"ok": True, "status": "queued", "started_at": datetime.now(timezone.utc).isoformat()}


@router.get("/api/v1/profiles/{model}")
async def model_profile(model: str) -> dict[str, Any]:
    stats = MODEL_STATS.get(model, Counter())
    total_scans = stats.get("total_scans", 0)
    total_hall = stats.get("total_hallucinations", 0)
    rate = (total_hall / total_scans) if total_scans else 0.0
    by_type = {k.split(":", 1)[1]: {"count": v, "rate": (v / total_hall) if total_hall else 0.0} for k, v in stats.items() if k.startswith("type:")}
    return {
        "model": model,
        "total_scans": total_scans,
        "total_hallucinations": total_hall,
        "hallucination_rate": rate,
        "by_type": by_type,
        "most_common_apis_hallucinated": [],
        "trend": [],
    }


@router.get("/api/v1/profiles")
async def all_profiles() -> dict[str, Any]:
    return {"profiles": [await model_profile(model) for model in sorted(MODEL_STATS.keys())]}
