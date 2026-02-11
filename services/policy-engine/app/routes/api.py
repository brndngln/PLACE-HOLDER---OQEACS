from fastapi import APIRouter

from app.models import BundleValidationRequest, PolicyCreateRequest, PolicyDecisionRequest
from app.services.core import PolicyEngineCore

router = APIRouter(prefix="/api/v1", tags=["policy-engine"])


def bind_routes(core: PolicyEngineCore) -> None:
    @router.post("/policies")
    async def create_policy(request: PolicyCreateRequest):
        return (await core.create_policy(request)).model_dump(mode="json")

    @router.get("/policies")
    async def list_policies():
        return [item.model_dump(mode="json") for item in await core.list_policies()]

    @router.get("/policies/{policy_id}")
    async def get_policy(policy_id: str):
        return (await core.get_policy(policy_id)).model_dump(mode="json")

    @router.post("/decisions/{policy_id}")
    async def evaluate(policy_id: str, request: PolicyDecisionRequest):
        return (await core.evaluate(policy_id, request)).model_dump(mode="json")

    @router.post("/bundles/validate")
    async def validate_bundle(request: BundleValidationRequest):
        return (await core.validate_bundle(request)).model_dump(mode="json")

    @router.get("/opa/status")
    async def opa_status():
        return await core.opa_status()
