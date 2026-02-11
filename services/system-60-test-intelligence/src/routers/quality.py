from __future__ import annotations

from fastapi import APIRouter

from src.models import GenerateTestsRequest
from src.services.flaky_detector import FlakyDetector
from src.services.impact_analyzer import TestImpactAnalyzer
from src.services.quality_scorer import TestQualityScorer
from src.services.test_generator import TestGenerator

router = APIRouter(prefix="/api/v1", tags=["quality"])


@router.post("/impact")
def impact(payload: dict):
    return TestImpactAnalyzer().analyze_impact(payload.get("changed_files", []), payload.get("test_map", {}))


@router.post("/quality/score")
def score(payload: dict):
    return TestQualityScorer().score_test_file(payload.get("test_code", ""), payload.get("file", "tests.py"))


@router.post("/generate-tests")
def generate(req: GenerateTestsRequest):
    return TestGenerator().generate(req)


@router.get("/flaky")
def flaky():
    sample = [
        {"test_name": "test_a", "passed": True},
        {"test_name": "test_a", "passed": False},
        {"test_name": "test_b", "passed": True},
    ]
    return FlakyDetector().detect_flaky(sample)
