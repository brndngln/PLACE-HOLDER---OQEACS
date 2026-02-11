from __future__ import annotations

from fastapi import APIRouter

from src.models import EvaluateRequest
from src.services.fitness_evaluator import FitnessEvaluator

router = APIRouter(prefix="/api/v1", tags=["evaluate"])
_reports: dict[str, dict] = {}


@router.post("/evaluate")
def evaluate(req: EvaluateRequest):
    result = FitnessEvaluator().evaluate(req.rules, req.codebase_path, req.layers)
    report_id = f"report-{len(_reports)+1}"
    _reports[report_id] = {"id": report_id, "result": result.model_dump()}
    return _reports[report_id]


@router.get("/report/{report_id}")
def report(report_id: str):
    return _reports.get(report_id, {"detail": "not found"})


@router.post("/rules")
def rules(payload: dict):
    return payload
