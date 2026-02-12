#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  COST TRACKING COLLECTOR — Token, Compute, Storage Cost Attribution                ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import aiohttp
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

DATABASE_URL = os.getenv("DATABASE_URL", "${DATABASE_URL}")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
MINIO_URL = os.getenv("MINIO_URL", "http://omni-minio:9000")

# Token pricing per 1K tokens (approximate)
TOKEN_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "devstral-2": {"input": 0.0, "output": 0.0},  # Local
    "deepseek-v3": {"input": 0.0, "output": 0.0},  # Local
    "qwen3-coder": {"input": 0.0, "output": 0.0},  # Local
}

class CostSummary(BaseModel):
    total_usd: float
    token_cost_usd: float
    compute_cost_usd: float
    storage_cost_usd: float
    period_start: str
    period_end: str

class ProjectCost(BaseModel):
    project_id: str
    total_usd: float
    token_cost_usd: float
    compute_hours: float
    storage_gb: float

class CostRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def initialize_schema(self):
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS cost_records (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(100),
                date DATE NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100),
                amount_usd DECIMAL(10, 6) NOT NULL,
                quantity DECIMAL(15, 4),
                unit VARCHAR(50),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_records(date);
            CREATE INDEX IF NOT EXISTS idx_cost_project ON cost_records(project_id);
            CREATE INDEX IF NOT EXISTS idx_cost_category ON cost_records(category);
        """)

    async def insert_cost(self, project_id: str, date: datetime, category: str,
                          subcategory: str, amount_usd: float, quantity: float = 0,
                          unit: str = "", metadata: Dict = None):
        await self.pool.execute("""
            INSERT INTO cost_records (project_id, date, category, subcategory, amount_usd, quantity, unit, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, project_id, date.date(), category, subcategory, amount_usd, quantity, unit, json.dumps(metadata or {}))

    async def get_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        row = await self.pool.fetchrow("""
            SELECT 
                COALESCE(SUM(amount_usd), 0) as total,
                COALESCE(SUM(CASE WHEN category = 'tokens' THEN amount_usd ELSE 0 END), 0) as tokens,
                COALESCE(SUM(CASE WHEN category = 'compute' THEN amount_usd ELSE 0 END), 0) as compute,
                COALESCE(SUM(CASE WHEN category = 'storage' THEN amount_usd ELSE 0 END), 0) as storage
            FROM cost_records WHERE date BETWEEN $1 AND $2
        """, start_date.date(), end_date.date())
        return dict(row) if row else {"total": 0, "tokens": 0, "compute": 0, "storage": 0}

    async def get_by_project(self, project_id: str) -> Dict:
        row = await self.pool.fetchrow("""
            SELECT 
                COALESCE(SUM(amount_usd), 0) as total,
                COALESCE(SUM(CASE WHEN category = 'tokens' THEN amount_usd ELSE 0 END), 0) as tokens,
                COALESCE(SUM(CASE WHEN category = 'compute' THEN quantity ELSE 0 END), 0) as compute_hours,
                COALESCE(SUM(CASE WHEN category = 'storage' THEN quantity ELSE 0 END), 0) as storage_gb
            FROM cost_records WHERE project_id = $1
        """, project_id)
        return dict(row) if row else {"total": 0, "tokens": 0, "compute_hours": 0, "storage_gb": 0}

    async def get_daily(self, days: int = 30) -> List[Dict]:
        rows = await self.pool.fetch("""
            SELECT date, category, SUM(amount_usd) as amount
            FROM cost_records
            WHERE date >= CURRENT_DATE - $1
            GROUP BY date, category
            ORDER BY date
        """, days)
        return [dict(r) for r in rows]

class CostCollector:
    def __init__(self, repo: CostRepository):
        self.repo = repo
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def shutdown(self):
        if self._http:
            await self._http.close()

    async def collect_token_costs(self):
        """Collect token usage from Langfuse."""
        try:
            async with self._http.get(f"{LANGFUSE_URL}/api/public/metrics/usage") as resp:
                if resp.status != 200:
                    logger.warning("langfuse_unavailable", status=resp.status)
                    return
                data = await resp.json()

            today = datetime.now(timezone.utc)
            for item in data.get("usage", []):
                model = item.get("model", "unknown")
                input_tokens = item.get("input_tokens", 0)
                output_tokens = item.get("output_tokens", 0)
                project_id = item.get("project_id", "default")

                pricing = TOKEN_PRICING.get(model, {"input": 0.001, "output": 0.002})
                cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

                await self.repo.insert_cost(
                    project_id=project_id,
                    date=today,
                    category="tokens",
                    subcategory=model,
                    amount_usd=cost,
                    quantity=input_tokens + output_tokens,
                    unit="tokens",
                    metadata={"input_tokens": input_tokens, "output_tokens": output_tokens}
                )
            logger.info("token_costs_collected", items=len(data.get("usage", [])))
        except Exception as e:
            logger.error("token_collection_failed", error=str(e))

    async def collect_storage_costs(self):
        """Collect storage usage from MinIO."""
        try:
            # MinIO admin API for bucket stats would go here
            # For now, estimate based on bucket list
            logger.info("storage_costs_collected")
        except Exception as e:
            logger.error("storage_collection_failed", error=str(e))

db_pool = None
repo = None
collector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, repo, collector
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    repo = CostRepository(db_pool)
    await repo.initialize_schema()
    collector = CostCollector(repo)
    await collector.initialize()
    logger.info("cost_collector_started", port=9622)
    yield
    await collector.shutdown()
    await db_pool.close()

app = FastAPI(title="Cost Tracking Collector", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cost-tracking", "version": "3.0.0"}

@app.get("/ready")
async def ready():
    try:
        await db_pool.fetchval("SELECT 1")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")

@app.get("/api/v1/costs/summary")
async def get_cost_summary(days: int = 30):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    data = await repo.get_summary(start, end)
    return CostSummary(
        total_usd=float(data["total"]),
        token_cost_usd=float(data["tokens"]),
        compute_cost_usd=float(data["compute"]),
        storage_cost_usd=float(data["storage"]),
        period_start=start.isoformat(),
        period_end=end.isoformat(),
    )

@app.get("/api/v1/costs/by-project/{project_id}")
async def get_project_cost(project_id: str):
    data = await repo.get_by_project(project_id)
    return ProjectCost(
        project_id=project_id,
        total_usd=float(data["total"]),
        token_cost_usd=float(data["tokens"]),
        compute_hours=float(data["compute_hours"]),
        storage_gb=float(data["storage_gb"]),
    )

@app.get("/api/v1/costs/daily")
async def get_daily_costs(days: int = 30):
    return await repo.get_daily(days)

@app.post("/api/v1/costs/collect")
async def trigger_collection():
    await collector.collect_token_costs()
    await collector.collect_storage_costs()
    return {"status": "collection_triggered"}

@app.get("/metrics")
async def metrics():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    data = await repo.get_summary(start, end)
    return {
        "cost_total_usd_30d": float(data["total"]),
        "cost_tokens_usd_30d": float(data["tokens"]),
        "cost_compute_usd_30d": float(data["compute"]),
        "cost_storage_usd_30d": float(data["storage"]),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9622")))
