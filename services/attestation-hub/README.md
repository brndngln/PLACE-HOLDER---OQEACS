# Attestation Hub

Supply-chain integrity control plane for Omni Quantum Elite. Provides in-toto statement generation, SLSA provenance payloads, signing, verification, and SBOM quality checks.

## Endpoints
- `POST /api/v1/attestations/provenance`
- `GET /api/v1/attestations/{attestation_id}`
- `POST /api/v1/attestations/{attestation_id}/sign`
- `POST /api/v1/attestations/{attestation_id}/verify`
- `POST /api/v1/sbom/ingest`
- `POST /api/v1/sbom/{sbom_id}/verify`
- `GET /api/v1/stats`

Infra:
- `/health`, `/ready`, `/metrics`, `/info`

## Security model
Current implementation uses HMAC signatures for deterministic verification within private infrastructure. For production-grade signing, integrate KMS/Sigstore-backed key material and publish attestations to OCI registry alongside artifact digests.
