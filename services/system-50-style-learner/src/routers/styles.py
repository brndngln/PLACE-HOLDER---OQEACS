from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.models import LearnRequest, StyleCheckRequest, StyleCheckResult, StyleProfile
from src.services.analyzer import StyleAnalyzer
from src.services.enforcer import StyleEnforcer

router = APIRouter(prefix="/api/v1", tags=["styles"])
_profiles: dict[str, StyleProfile] = {}


@router.post("/learn", response_model=StyleProfile)
def learn(req: LearnRequest) -> StyleProfile:
    analyzer = StyleAnalyzer()
    profile = analyzer.analyze_repo(req.repo_path)
    _profiles[profile.id] = profile
    return profile


@router.get("/profiles/{profile_id}", response_model=StyleProfile)
def get_profile(profile_id: str) -> StyleProfile:
    if profile_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profiles[profile_id]


@router.post("/check", response_model=StyleCheckResult)
def check(req: StyleCheckRequest) -> StyleCheckResult:
    profile = _profiles.get(req.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return StyleEnforcer().check_code(req.code, profile)
