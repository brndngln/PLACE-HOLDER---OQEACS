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


def test_create_policy_and_decision() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            policy = await client.post(
                "/api/v1/policies",
                json={
                    "name": "deploy-guard",
                    "package_path": "omni/policies/deploy",
                    "entrypoint": "allow",
                    "rego": "package omni.policies.deploy\n\ndefault allow := false\n\nallow if { input.allow == true }\n",
                },
            )
            assert policy.status_code == 200
            policy_id = policy.json()["id"]

            decision = await client.post(f"/api/v1/decisions/{policy_id}", json={"input": {"allow": True}})
            assert decision.status_code == 200
            assert decision.json()["decision"] is True

    asyncio.run(_run())


def test_bundle_validation() -> None:
    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bundles/validate",
                json={
                    "files": {
                        "deploy.rego": "package omni.policies.deploy\n\ndefault allow := false\nallow if { input.ok == true }"
                    }
                },
            )
        assert response.status_code == 200
        assert response.json()["valid"] is True

    asyncio.run(_run())
