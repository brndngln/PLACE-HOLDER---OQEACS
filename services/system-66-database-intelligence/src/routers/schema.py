from __future__ import annotations

from fastapi import APIRouter

from src.services.schema_reviewer import SchemaReviewer

router = APIRouter(prefix="/api/v1", tags=["schema"])


@router.post("/schema/review")
def review(payload: dict):
    return SchemaReviewer().review(payload.get("schema_sql", ""))
