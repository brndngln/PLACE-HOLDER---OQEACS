from __future__ import annotations

from fastapi import APIRouter

from src.services.mutation_engine import MutationEngine

router = APIRouter(prefix="/api/v1", tags=["mutation"])
_store: dict[str, dict] = {}


@router.post("/mutate")
def mutate(payload: dict):
    code = payload.get("code", "")
    language = payload.get("language", "python")
    result = MutationEngine().mutate(code, language)
    run_id = f"mut-{len(_store)+1}"
    _store[run_id] = result.model_dump()
    return {"id": run_id, **_store[run_id]}


@router.get("/mutation/{run_id}")
def get_mutation(run_id: str):
    return _store.get(run_id, {"detail": "not found"})
