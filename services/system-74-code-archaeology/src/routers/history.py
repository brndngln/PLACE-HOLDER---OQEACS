from __future__ import annotations

from fastapi import APIRouter

from src.services.biography_builder import BiographyBuilder
from src.services.deletion_analyzer import DeletionAnalyzer
from src.services.git_analyzer import GitAnalyzer

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history")
def history(repo_path: str, file: str, function: str):
    return GitAnalyzer().get_function_history(repo_path, file, function)


@router.post("/biography")
def biography(payload: dict):
    return BiographyBuilder().build(payload["repo_path"], payload["file"], payload["function"])


@router.post("/deletion-risk")
def deletion_risk(payload: dict):
    return DeletionAnalyzer().assess_deletion_risk(payload["repo_path"], payload["file"], payload["function"])
