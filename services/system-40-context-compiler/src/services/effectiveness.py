"""Effectiveness tracking — learns which context blocks improve output quality."""
import json

import asyncpg
import structlog

from src.models import BlockEffectiveness, ContextBlock, EffectivenessReport

logger = structlog.get_logger()


class EffectivenessTracker:
    """Tracks which context blocks correlate with higher quality scores."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def record(self, report: EffectivenessReport, blocks_used: list[ContextBlock]) -> None:
        """Record effectiveness of a context compilation."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO context_effectiveness (
                    task_id, context_hash, quality_score, task_success,
                    blocks_json, created_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                """,
                report.task_id,
                report.context_hash,
                report.output_quality_score,
                report.task_success,
                json.dumps([b.model_dump() for b in blocks_used]),
            )
        logger.info(
            "effectiveness_recorded",
            task_id=report.task_id,
            quality=report.output_quality_score,
            success=report.task_success,
        )

    async def get_block_effectiveness(self, source: str, days: int = 30) -> BlockEffectiveness:
        """Which context sources correlate with higher quality scores?"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    AVG(quality_score) as avg_quality,
                    COUNT(*) as usage_count,
                    AVG(CASE WHEN task_success THEN 1.0 ELSE 0.0 END) as success_rate
                FROM context_effectiveness
                WHERE created_at > NOW() - make_interval(days => $1)
                  AND blocks_json::text LIKE $2
                """,
                days,
                f'%"{source}"%',
            )
            if row and row["usage_count"] > 0:
                return BlockEffectiveness(
                    source=source,
                    avg_quality=float(row["avg_quality"]),
                    usage_count=int(row["usage_count"]),
                    success_rate=float(row["success_rate"]),
                )
            return BlockEffectiveness(source=source, avg_quality=0.0, usage_count=0, success_rate=0.0)

    async def get_stats(self, days: int = 30) -> dict:
        """Get aggregate stats on context compilation effectiveness."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    AVG(quality_score) as avg_quality,
                    AVG(CASE WHEN task_success THEN 1.0 ELSE 0.0 END) as success_rate
                FROM context_effectiveness
                WHERE created_at > NOW() - make_interval(days => $1)
                """,
                days,
            )
            return {
                "total_compilations": int(row["total"]) if row else 0,
                "avg_quality_score": float(row["avg_quality"]) if row and row["avg_quality"] else 0.0,
                "success_rate": float(row["success_rate"]) if row and row["success_rate"] else 0.0,
            }
