from fastapi import APIRouter

from app.models import ProvenanceCreateRequest, SbomIngestRequest, VerifyRequest
from app.services.core import AttestationHubCore

router = APIRouter(prefix="/api/v1", tags=["attestation-hub"])


def bind_routes(core: AttestationHubCore) -> None:
    @router.post("/attestations/provenance")
    async def create_provenance(request: ProvenanceCreateRequest):
        return (await core.create_provenance(request)).model_dump(mode="json")

    @router.get("/attestations/{attestation_id}")
    async def get_attestation(attestation_id: str):
        return (await core.get_attestation(attestation_id)).model_dump(mode="json")

    @router.post("/attestations/{attestation_id}/sign")
    async def sign_attestation(attestation_id: str):
        return (await core.sign_attestation(attestation_id)).model_dump(mode="json")

    @router.post("/attestations/{attestation_id}/verify")
    async def verify_attestation(attestation_id: str, request: VerifyRequest):
        return (await core.verify_attestation(attestation_id, request.signature)).model_dump(mode="json")

    @router.post("/sbom/ingest")
    async def ingest_sbom(request: SbomIngestRequest):
        return (await core.ingest_sbom(request)).model_dump(mode="json")

    @router.post("/sbom/{sbom_id}/verify")
    async def verify_sbom(sbom_id: str):
        return (await core.verify_sbom(sbom_id)).model_dump(mode="json")

    @router.get("/stats")
    async def stats():
        return (await core.stats()).model_dump(mode="json")
