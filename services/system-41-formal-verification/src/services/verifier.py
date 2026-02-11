"""Main verification orchestrator — ties together tool selection, execution, and storage."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

import asyncpg
import redis.asyncio as aioredis
import structlog

from src.config import Settings
from src.models import (
    ProofRecord,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
    VerificationTool,
)
from src.services.tool_registry import run_verification, select_tool
from src.utils.notifications import notify_mattermost

logger = structlog.get_logger()


class VerificationService:
    """Orchestrates formal verification requests."""

    def __init__(
        self,
        pool: asyncpg.Pool | None,
        redis_client: aioredis.Redis,
        settings: Settings,
    ) -> None:
        self.pool = pool
        self.redis = redis_client
        self.settings = settings

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        """Submit code for formal verification."""
        tool_id = select_tool(request.language, request.tool)
        properties = request.properties or ["correctness"]

        logger.info(
            "verification_started",
            tool=tool_id,
            language=request.language,
            properties=properties,
        )

        result = await run_verification(
            tool_id=tool_id,
            source_code=request.source_code,
            properties=properties,
            settings=self.settings,
            depth=request.depth,
        )

        await self._store_result(result, request.project_id)

        if result.status == VerificationStatus.FAILED and result.counterexamples:
            await notify_mattermost(
                webhook_url=self.settings.MATTERMOST_WEBHOOK_URL,
                channel="formal-verification",
                message=(
                    f"Verification FAILED for {request.language} code using {tool_id}. "
                    f"{len(result.counterexamples)} counterexample(s) found. "
                    f"Properties failed: {', '.join(result.properties_failed)}"
                ),
                service_name=self.settings.SERVICE_NAME,
                severity="warning",
            )
        elif result.status == VerificationStatus.PASSED:
            await notify_mattermost(
                webhook_url=self.settings.MATTERMOST_WEBHOOK_URL,
                channel="formal-verification",
                message=(
                    f"Verification PASSED for {request.language} code using {tool_id}. "
                    f"All {len(result.properties_passed)} properties verified."
                ),
                service_name=self.settings.SERVICE_NAME,
                severity="success",
            )

        await self.redis.setex(
            f"verification:{result.id}",
            3600,
            json.dumps(result.model_dump(), default=str),
        )

        return result

    async def get_result(self, result_id: str) -> VerificationResult | None:
        """Get a verification result by ID."""
        cached = await self.redis.get(f"verification:{result_id}")
        if cached:
            data = json.loads(cached)
            return VerificationResult(**data)

        if self.pool is None:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT result_json FROM verification_results WHERE id = $1",
                result_id,
            )
            if row:
                return VerificationResult(**json.loads(row["result_json"]))
        return None

    async def list_proofs(
        self, project_id: str | None = None, limit: int = 50
    ) -> list[ProofRecord]:
        """List completed verification proofs."""
        if self.pool is None:
            return []

        async with self.pool.acquire() as conn:
            if project_id:
                rows = await conn.fetch(
                    """
                    SELECT id, project_id, tool, status, properties_count,
                           properties_passed, execution_time_ms, created_at
                    FROM verification_results
                    WHERE project_id = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    project_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, project_id, tool, status, properties_count,
                           properties_passed, execution_time_ms, created_at
                    FROM verification_results
                    ORDER BY created_at DESC LIMIT $1
                    """,
                    limit,
                )

            return [
                ProofRecord(
                    id=row["id"],
                    project_id=row["project_id"],
                    tool=VerificationTool(row["tool"]),
                    status=VerificationStatus(row["status"]),
                    properties_count=row["properties_count"],
                    properties_passed=row["properties_passed"],
                    execution_time_ms=row["execution_time_ms"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    async def _store_result(self, result: VerificationResult, project_id: str | None) -> None:
        """Store verification result in PostgreSQL."""
        if self.pool is None:
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO verification_results (
                        id, project_id, tool, status, properties_count,
                        properties_passed, execution_time_ms, result_json, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
                    """,
                    result.id,
                    project_id,
                    result.tool.value,
                    result.status.value,
                    len(result.properties_checked),
                    len(result.properties_passed),
                    result.execution_time_ms,
                    json.dumps(result.model_dump(), default=str),
                    result.created_at,
                )
        except Exception as exc:
            logger.warning("store_result_failed", error=str(exc))
