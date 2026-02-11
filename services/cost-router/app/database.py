from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


engine = None
SessionLocal = None

if settings.database_url:
    engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def check_database() -> bool:
    if engine is None:
        return True
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def get_session() -> AsyncSession:
    if SessionLocal is None:
        raise RuntimeError("database not configured")
    async with SessionLocal() as session:
        yield session
