from __future__ import annotations

from fastapi import APIRouter

from src.models import MigrationRequest, MigrationRule
from src.services.migration_engine import MigrationEngine
from src.services.rule_registry import RuleRegistry

router = APIRouter(prefix="/api/v1", tags=["migrate"])
_registry = RuleRegistry()
_engine = MigrationEngine(_registry)


@router.post("/migrate")
def migrate(req: MigrationRequest):
    return _engine.migrate(req)


@router.get("/migrations")
def migrations():
    return _registry.list_supported_migrations()


@router.post("/rules")
def add_rule(payload: dict):
    rule = MigrationRule(**payload["rule"])
    _registry.add_rule(payload["source"], payload["target"], rule)
    return {"status": "ok"}
