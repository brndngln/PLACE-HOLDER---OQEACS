from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models import InstrumentationCheckRequest
from app.services.core import ObservabilityCore

router = APIRouter(prefix="/api/v1", tags=["observability-otel"])


class SamplingUpdate(BaseModel):
    ratio: float = Field(ge=0.0, le=1.0)


def bind_routes(core: ObservabilityCore) -> None:
    @router.get("/pipelines")
    async def pipelines():
        return await core.get_pipelines()

    @router.get("/pipelines/sampling")
    async def get_sampling():
        return (await core.get_sampling()).model_dump(mode="json")

    @router.put("/pipelines/sampling")
    async def set_sampling(request: SamplingUpdate):
        return (await core.set_sampling(request.ratio)).model_dump(mode="json")

    @router.post("/instrumentation/check")
    async def instrumentation_check(request: InstrumentationCheckRequest):
        return (await core.instrumentation_check(request)).model_dump(mode="json")

    @router.get("/collector/status")
    async def collector_status():
        return (await core.collector_status()).model_dump(mode="json")
