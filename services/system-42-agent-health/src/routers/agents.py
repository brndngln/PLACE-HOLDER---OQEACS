"""
System 42 — Agent endpoints.

GET /api/v1/agents                  — list all known agents
GET /api/v1/agents/{agent_id}/health  — health summary for one agent
GET /api/v1/agents/{agent_id}/history — historical performance data
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.models import AgentHealthSummary

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get(
    "",
    summary="List known agents",
    response_model=list[str],
)
async def list_agents(request: Request) -> list[str]:
    """Return every agent ID known to the health monitor."""
    monitor = request.app.state.monitor
    agents = await monitor.list_agents()
    return agents


@router.get(
    "/{agent_id}/health",
    summary="Agent health summary",
    response_model=AgentHealthSummary,
)
async def get_agent_health(agent_id: str, request: Request) -> AgentHealthSummary:
    """Compute and return the current health summary for *agent_id*."""
    monitor = request.app.state.monitor
    try:
        summary = await monitor.get_agent_health(agent_id)
    except Exception as exc:
        logger.error("agent_health_error", agent_id=agent_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return summary


@router.get(
    "/{agent_id}/history",
    summary="Agent performance history",
    response_model=list[dict[str, Any]],
)
async def get_agent_history(
    agent_id: str,
    request: Request,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Return raw performance-history rows for *agent_id* over the last
    *days* days."""
    monitor = request.app.state.monitor
    try:
        drift_report = await monitor.drift_detector.detect_drift(agent_id, days=days)
        return drift_report.history
    except Exception as exc:
        logger.error("agent_history_error", agent_id=agent_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
