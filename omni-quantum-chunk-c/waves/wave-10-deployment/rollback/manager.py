#!/usr/bin/env python3
# ROLLBACK MANAGER — OMNI QUANTUM ELITE v3.0
import asyncio, os, json, subprocess, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional
import aiohttp, asyncpg, structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
logger = structlog.get_logger()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fortress:quantum_elite_2024@omni-postgres:5432/financial_fortress")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK_URL", "")

class RollbackRequest(BaseModel):
    service: str
    target_version: Optional[str] = None
    reason: str = ""

class RollbackResult(BaseModel):
    success: bool
    service: str
    from_version: str
    to_version: str
    duration_ms: int
    error: Optional[str] = None

class RollbackRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def initialize_schema(self):
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS deployment_history (
                id SERIAL PRIMARY KEY, service VARCHAR(100) NOT NULL, version VARCHAR(100) NOT NULL,
                image VARCHAR(500) NOT NULL, deployed_at TIMESTAMPTZ DEFAULT NOW(), deployed_by VARCHAR(100) DEFAULT 'system',
                is_current BOOLEAN DEFAULT FALSE, config JSONB DEFAULT '{}', UNIQUE(service, version)
            )""")

    async def get_current(self, service: str) -> Optional[Dict]:
        row = await self.pool.fetchrow("SELECT * FROM deployment_history WHERE service = $1 AND is_current = TRUE", service)
        return dict(row) if row else None

    async def get_previous(self, service: str) -> Optional[Dict]:
        row = await self.pool.fetchrow("""SELECT * FROM deployment_history WHERE service = $1 AND is_current = FALSE ORDER BY deployed_at DESC LIMIT 1""", service)
        return dict(row) if row else None

    async def set_current(self, service: str, version: str):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE deployment_history SET is_current = FALSE WHERE service = $1", service)
                await conn.execute("UPDATE deployment_history SET is_current = TRUE WHERE service = $1 AND version = $2", service, version)

class RollbackManager:
    def __init__(self, repo: RollbackRepository):
        self.repo = repo
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def shutdown(self):
        if self._http:
            await self._http.close()

    async def rollback(self, request: RollbackRequest) -> RollbackResult:
        start_time = time.time()
        current = await self.repo.get_current(request.service)
        if not current:
            return RollbackResult(success=False, service=request.service, from_version="unknown", to_version="unknown", duration_ms=0, error="No history")
        target = await self.repo.get_previous(request.service) if not request.target_version else None
        if not target:
            return RollbackResult(success=False, service=request.service, from_version=current["version"], to_version="previous", duration_ms=int((time.time() - start_time) * 1000), error="Target not found")
        logger.info("rolling_back", service=request.service, from_version=current["version"], to_version=target["version"])
        await self.repo.set_current(request.service, target["version"])
        return RollbackResult(success=True, service=request.service, from_version=current["version"], to_version=target["version"], duration_ms=int((time.time() - start_time) * 1000))

db_pool = None
repo = None
manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, repo, manager
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    repo = RollbackRepository(db_pool)
    await repo.initialize_schema()
    manager = RollbackManager(repo)
    await manager.initialize()
    logger.info("rollback_manager_started", port=9652)
    yield
    await manager.shutdown()
    await db_pool.close()

app = FastAPI(title="Rollback Manager", version="3.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rollback-manager", "version": "3.0.0"}

@app.post("/api/v1/rollback")
async def execute_rollback(request: RollbackRequest):
    return await manager.rollback(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9652")))
