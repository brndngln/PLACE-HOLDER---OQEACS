from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.exceptions import ServiceError
from app.models import (
    AttestationRecord,
    HubStats,
    ProvenanceCreateRequest,
    SbomIngestRequest,
    SbomRecord,
    SbomVerifyResponse,
    SignatureResponse,
    VerifyResponse,
)

IN_TOTO_TYPE = "https://in-toto.io/Statement/v1"
SLSA_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"


class AttestationHubCore:
    def __init__(self, data_path: str, hmac_key: str, default_builder_id: str) -> None:
        self._path = Path(data_path)
        self._hmac_key = hmac_key.encode("utf-8")
        self._default_builder_id = default_builder_id
        self._attestations: dict[str, AttestationRecord] = {}
        self._sboms: dict[str, SbomRecord] = {}

    async def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            await self._persist()
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        self._attestations = {
            row["id"]: AttestationRecord.model_validate(row) for row in payload.get("attestations", [])
        }
        self._sboms = {row["id"]: SbomRecord.model_validate(row) for row in payload.get("sboms", [])}

    async def _persist(self) -> None:
        payload = {
            "attestations": [item.model_dump(mode="json") for item in self._attestations.values()],
            "sboms": [item.model_dump(mode="json") for item in self._sboms.values()],
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    async def create_provenance(self, request: ProvenanceCreateRequest) -> AttestationRecord:
        statement = {
            "_type": IN_TOTO_TYPE,
            "subject": [{"name": request.artifact_name, "digest": {"sha256": request.digest_sha256}}],
            "predicateType": SLSA_PREDICATE_TYPE,
            "predicate": {
                "buildDefinition": {
                    "buildType": request.build_type,
                    "externalParameters": request.invocation,
                },
                "runDetails": {
                    "builder": {"id": request.builder_id or self._default_builder_id},
                    "metadata": {
                        "invocationId": f"inv-{uuid4().hex[:12]}",
                        "startedOn": datetime.now(timezone.utc).isoformat(),
                        "finishedOn": datetime.now(timezone.utc).isoformat(),
                    },
                },
                "omni": request.metadata,
            },
        }
        record = AttestationRecord(
            id=f"att-{uuid4().hex[:12]}",
            statement=statement,
            created_at=datetime.now(timezone.utc),
        )
        self._attestations[record.id] = record
        await self._persist()
        return record

    async def get_attestation(self, attestation_id: str) -> AttestationRecord:
        record = self._attestations.get(attestation_id)
        if not record:
            raise ServiceError("attestation not found", status_code=404, code="attestation_not_found")
        return record

    def _signature_for_statement(self, statement: dict[str, Any]) -> str:
        canonical = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._hmac_key, canonical, hashlib.sha256).hexdigest()

    async def sign_attestation(self, attestation_id: str) -> SignatureResponse:
        record = await self.get_attestation(attestation_id)
        signature = self._signature_for_statement(record.statement)
        record.signature = signature
        await self._persist()
        return SignatureResponse(attestation_id=attestation_id, signature=signature, algorithm="hmac-sha256")

    async def verify_attestation(self, attestation_id: str, signature: str) -> VerifyResponse:
        record = await self.get_attestation(attestation_id)
        expected = self._signature_for_statement(record.statement)
        verified = hmac.compare_digest(expected, signature)
        return VerifyResponse(
            attestation_id=attestation_id,
            verified=verified,
            detail="signature valid" if verified else "signature mismatch",
        )

    async def ingest_sbom(self, request: SbomIngestRequest) -> SbomRecord:
        record = SbomRecord(
            id=f"sbm-{uuid4().hex[:12]}",
            format=request.format,
            document=request.document,
            created_at=datetime.now(timezone.utc),
        )
        self._sboms[record.id] = record
        await self._persist()
        return record

    async def verify_sbom(self, sbom_id: str) -> SbomVerifyResponse:
        record = self._sboms.get(sbom_id)
        if not record:
            raise ServiceError("sbom not found", status_code=404, code="sbom_not_found")

        errors: list[str] = []
        if record.format == "spdx":
            if "SPDXID" not in record.document:
                errors.append("missing SPDXID")
            if "packages" not in record.document:
                errors.append("missing packages")
        if record.format == "cyclonedx":
            if "bomFormat" not in record.document:
                errors.append("missing bomFormat")
            if "components" not in record.document:
                errors.append("missing components")

        return SbomVerifyResponse(sbom_id=sbom_id, valid=not errors, errors=errors)

    async def stats(self) -> HubStats:
        records = list(self._attestations.values())
        return HubStats(
            attestations_total=len(records),
            signed_total=sum(1 for item in records if bool(item.signature)),
            sboms_total=len(self._sboms),
        )
