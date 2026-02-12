# Systems 45–58 Hardening Pass (Extreme Grade)

## What this package now enforces

| Control Area | Validator/Test | Evidence Type |
|---|---|---|
| Compose semantic conformance | `validate_compose_conformance.py` | YAML structure + per-service policy assertions |
| SDK API conformance | `validate_sdk_conformance.py` | AST class/method/decorator checks |
| Runtime contract baselines | `validate_runtime_contracts.py` | Audit endpoint presence + auth/security + init invariants |
| CI test execution | `test_hardening_validators.py` | Programmatic gate over all validators |

## Coverage highlights

- Semantic Compose checks for all 8 systems:
  - required restart policy
  - healthcheck presence
  - resource limits
  - `json-file` logging bounds
  - required Omni labels
  - external `omni-quantum-network` attachment
- SDK checks for all 8 clients:
  - required public API methods
  - internal `_get`/`_post`
  - retry decorator presence
  - required stack (`httpx`, `structlog`, tenacity)
- Runtime contract checks:
  - required Audit Logger routes
  - constant-time API-key comparison
  - batch-size guardrails
  - init scripts strict mode + bounded waits + idempotent webhook markers

## Security posture

- `AUDIT_API_KEY` is required by default for protected endpoints.
- Temporary insecure mode exists only via explicit override:
  - `ALLOW_INSECURE_UNAUTH=true`

## Execute all hardening gates

```bash
python omni-quantum-systems/hardening/scripts/validate_compose_conformance.py
python omni-quantum-systems/hardening/scripts/validate_sdk_conformance.py
python omni-quantum-systems/hardening/scripts/validate_runtime_contracts.py
python -m pytest -q omni-quantum-systems/hardening/tests/test_hardening_validators.py
```

## Operational rollout sequence

1. Run hardening validators locally.
2. Run validators in CI as mandatory checks.
3. Deploy to staging and verify `/ready` + `/metrics` across services.
4. Promote to production only when all hardening gates pass.
