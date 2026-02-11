import asyncio

import httpx

from app.main import app


def test_health() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200

    asyncio.run(_run())


def test_attestation_sign_and_verify() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post(
                "/api/v1/attestations/provenance",
                json={
                    "artifact_name": "omni-policy-engine:1.0.0",
                    "digest_sha256": "a" * 64,
                    "invocation": {"pipeline": "build-forge"},
                    "metadata": {"commit": "abc123"},
                },
            )
            assert create.status_code == 200
            attestation_id = create.json()["id"]

            sign = await client.post(f"/api/v1/attestations/{attestation_id}/sign")
            assert sign.status_code == 200
            signature = sign.json()["signature"]

            verify = await client.post(f"/api/v1/attestations/{attestation_id}/verify", json={"signature": signature})
            assert verify.status_code == 200
            assert verify.json()["verified"] is True

    asyncio.run(_run())


def test_sbom_ingest_and_verify() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            ingest = await client.post(
                "/api/v1/sbom/ingest",
                json={"format": "spdx", "document": {"SPDXID": "SPDXRef-DOCUMENT", "packages": []}},
            )
            assert ingest.status_code == 200
            sbom_id = ingest.json()["id"]

            verify = await client.post(f"/api/v1/sbom/{sbom_id}/verify")
            assert verify.status_code == 200
            assert verify.json()["valid"] is True

    asyncio.run(_run())
