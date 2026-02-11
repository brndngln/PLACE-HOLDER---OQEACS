from __future__ import annotations

from fastapi import APIRouter

from src.services.platform_client import PlatformClient

router = APIRouter(prefix="/api/v1", tags=["status"])


@router.get("/platform-status")
async def platform_status():
    return await PlatformClient().get_status()


@router.get("/services")
async def services():
    status = await PlatformClient().get_status()
    return status.services
