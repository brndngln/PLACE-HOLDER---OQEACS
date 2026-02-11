from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from src.models import ChaosExperiment
from src.services.experiment_runner import ExperimentRunner

router = APIRouter(prefix="/api/v1", tags=["experiments"])
_experiments: dict[str, ChaosExperiment] = {}
_results: dict[str, dict] = {}


@router.post("/experiments")
def create(payload: dict):
    exp = ChaosExperiment(id=str(uuid.uuid4()), **payload)
    _experiments[exp.id] = exp
    return exp


@router.get("/experiments")
def list_experiments():
    return list(_experiments.values())


@router.get("/experiments/{exp_id}")
def get_experiment(exp_id: str):
    if exp_id not in _experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _experiments[exp_id]


@router.post("/experiments/{exp_id}/run")
def run(exp_id: str):
    exp = _experiments.get(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    res = ExperimentRunner().run(exp)
    _results[exp_id] = res.model_dump()
    return res
