from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.models import IngestRequest, PredictRequest
from src.services.fix_library import FixLibrary
from src.services.ingester import ErrorIngester
from src.services.pattern_matcher import PatternMatcher
from src.services.predictor import ErrorPredictor

router = APIRouter(prefix="/api/v1", tags=["errors"])
_store = {}
_matcher = PatternMatcher(_store)
_ingester = ErrorIngester(_store, _matcher)
_predictor = ErrorPredictor()
_fixes = FixLibrary()


@router.post("/ingest")
def ingest(req: IngestRequest):
    pattern = _ingester.ingest(req)
    if not _fixes.get_fix(pattern.id):
        _fixes.store_fix(pattern.id, _fixes.auto_generate_fix(pattern.id))
    return pattern


@router.post("/predict")
def predict(req: PredictRequest):
    return _predictor.predict_errors(req.code, req.language)


@router.get("/patterns")
def patterns():
    return list(_store.values())


@router.get("/patterns/{pattern_id}")
def pattern(pattern_id: str):
    p = _store.get(pattern_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return p
