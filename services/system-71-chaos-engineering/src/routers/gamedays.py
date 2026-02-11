from __future__ import annotations

import uuid

from fastapi import APIRouter

from src.models import GameDay
from src.services.game_day_manager import GameDayManager

router = APIRouter(prefix="/api/v1", tags=["gamedays"])
_mgr = GameDayManager()


@router.post("/gamedays")
def create(payload: dict):
    gd = GameDay(id=str(uuid.uuid4()), **payload)
    return _mgr.schedule_game_day(gd)


@router.get("/gamedays")
def gamedays():
    return []


@router.get("/resilience/{service}")
def resilience(service: str):
    return _mgr.generate_report("none", service)
