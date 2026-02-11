from __future__ import annotations

from typing import Any

import httpx


class AttestationHubClient:
    def __init__(self, base_url: str = "http://omni-attestation-hub:9653", timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AttestationHubClient":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def create_provenance(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/attestations/provenance", json=payload)
        r.raise_for_status()
        return r.json()

    async def get_attestation(self, attestation_id: str) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/attestations/{attestation_id}")
        r.raise_for_status()
        return r.json()

    async def sign_attestation(self, attestation_id: str) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/attestations/{attestation_id}/sign")
        r.raise_for_status()
        return r.json()

    async def verify_attestation(self, attestation_id: str, signature: str) -> dict[str, Any]:
        r = await self.client.post(
            f"{self._base_url}/api/v1/attestations/{attestation_id}/verify",
            json={"signature": signature},
        )
        r.raise_for_status()
        return r.json()

    async def ingest_sbom(self, format_name: str, document: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/sbom/ingest", json={"format": format_name, "document": document})
        r.raise_for_status()
        return r.json()

    async def verify_sbom(self, sbom_id: str) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/sbom/{sbom_id}/verify")
        r.raise_for_status()
        return r.json()

    async def stats(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/stats")
        r.raise_for_status()
        return r.json()
