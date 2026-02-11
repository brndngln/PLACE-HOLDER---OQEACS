from __future__ import annotations

from fastapi import APIRouter

from src.models import ABTestConfig, PromptOptimizeRequest
from src.services.ab_tester import ABTester
from src.services.decay_detector import DecayDetector
from src.services.optimizer import PromptOptimizer

router = APIRouter(prefix="/api/v1", tags=["experiments"])
_tests: dict[str, dict] = {}


@router.post("/ab-test")
def ab_test(payload: dict):
    config = ABTestConfig(**payload["config"])
    result = ABTester().run_test(config, payload.get("scores_a", []), payload.get("scores_b", []))
    tid = f"ab-{len(_tests)+1}"
    _tests[tid] = result.model_dump()
    return {"id": tid, **_tests[tid]}


@router.get("/ab-test/{test_id}")
def get_test(test_id: str):
    return _tests.get(test_id, {"detail": "not found"})


@router.post("/optimize")
def optimize(req: PromptOptimizeRequest):
    return PromptOptimizer().optimize(req)


@router.get("/decay/{prompt_id}")
def decay(prompt_id: str, baseline: float = 0.9):
    return DecayDetector().check_decay(prompt_id, baseline, [0.88, 0.86, 0.84])
