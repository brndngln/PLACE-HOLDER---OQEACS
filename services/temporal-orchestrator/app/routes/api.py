from fastapi import APIRouter

from app.models import WorkflowDefinitionCreate, WorkflowSignalRequest, WorkflowStartRequest
from app.services.core import TemporalControlPlane

router = APIRouter(prefix="/api/v1", tags=["temporal-orchestrator"])


def bind_routes(control_plane: TemporalControlPlane) -> None:
    @router.post("/workflows/definitions")
    async def create_definition(request: WorkflowDefinitionCreate):
        return (await control_plane.register_definition(request)).model_dump(mode="json")

    @router.get("/workflows/definitions")
    async def list_definitions():
        return [item.model_dump(mode="json") for item in await control_plane.list_definitions()]

    @router.post("/workflows/runs")
    async def start_run(request: WorkflowStartRequest):
        return (await control_plane.start_run(request)).model_dump(mode="json")

    @router.get("/workflows/runs")
    async def list_runs():
        return [item.model_dump(mode="json") for item in await control_plane.list_runs()]

    @router.get("/workflows/runs/{run_id}")
    async def get_run(run_id: str):
        return (await control_plane.get_run(run_id)).model_dump(mode="json")

    @router.post("/workflows/runs/{run_id}/signal")
    async def signal_run(run_id: str, request: WorkflowSignalRequest):
        return (await control_plane.signal_run(run_id, request)).model_dump(mode="json")

    @router.post("/workflows/runs/{run_id}/terminate")
    async def terminate_run(run_id: str):
        return (await control_plane.terminate_run(run_id)).model_dump(mode="json")

    @router.get("/workflows/stats")
    async def stats():
        return (await control_plane.stats()).model_dump(mode="json")
