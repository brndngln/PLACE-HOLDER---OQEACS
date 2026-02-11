from __future__ import annotations

from fastapi import APIRouter

from src.models import LoRAConfig
from src.services.evaluator import ModelEvaluator
from src.services.training_orchestrator import TrainingOrchestrator

router = APIRouter(prefix="/api/v1", tags=["training"])
_orch = TrainingOrchestrator()


@router.post("/train")
def train(payload: dict):
    cfg = LoRAConfig(**payload.get("lora_config", {}))
    return _orch.start_job(payload["base_model"], payload["dataset_id"], cfg)


@router.get("/jobs")
def jobs():
    return _orch.list_jobs()


@router.get("/jobs/{job_id}")
def job(job_id: str):
    return _orch.get_job(job_id) or {"detail": "not found"}


@router.get("/evaluate/{job_id}")
def evaluate(job_id: str):
    job = _orch.get_job(job_id)
    if not job:
        return {"detail": "not found"}
    results = ModelEvaluator().evaluate(f"models/{job_id}", ["HumanEval", "CustomCoding"])
    _orch.complete_job(job_id, [r.model_dump() for r in results])
    return results
