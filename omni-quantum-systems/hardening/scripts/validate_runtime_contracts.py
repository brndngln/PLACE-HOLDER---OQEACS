from __future__ import annotations

import ast
from pathlib import Path

AUDIT_APP = Path("omni-quantum-systems/system-55-audit-logger/app/main.py")
INIT_SCRIPTS = [
    Path("omni-quantum-systems/system-45-email-service/scripts/init.sh"),
    Path("omni-quantum-systems/system-47-support-center/scripts/init.sh"),
    Path("omni-quantum-systems/system-48-web-analytics/scripts/init.sh"),
    Path("omni-quantum-systems/system-50-feature-flags/scripts/init.sh"),
    Path("omni-quantum-systems/system-51-error-tracking/scripts/init.sh"),
    Path("omni-quantum-systems/system-52-search-engine/scripts/init.sh"),
    Path("omni-quantum-systems/system-58-translation-management/scripts/init.sh"),
]

REQUIRED_AUDIT_ROUTES = {
    "/events",
    "/events/batch",
    "/events/{event_id}",
    "/events/timeline/{resource_type}/{resource_id}",
    "/events/actor/{actor_id}",
    "/events/summary",
    "/events/export",
    "/health",
    "/ready",
    "/metrics",
}


def validate_audit_routes() -> list[str]:
    failures: list[str] = []
    tree = ast.parse(AUDIT_APP.read_text())
    route_paths: set[str] = set()
    has_api_key_dependency = False

    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app" and dec.func.attr in {"get", "post"}:
                        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                            route_paths.add(dec.args[0].value)
            for arg in node.args.args:
                ann = arg.annotation
                if isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name) and ann.value.id == "Depends":
                    has_api_key_dependency = True

    missing = REQUIRED_AUDIT_ROUTES - route_paths
    if missing:
        failures.append(f"audit routes missing: {sorted(missing)}")

    content = AUDIT_APP.read_text()
    if "hmac.compare_digest" not in content:
        failures.append("audit app missing constant-time api key compare")
    if "MAX_BATCH_SIZE" not in content:
        failures.append("audit app missing batch guard")

    if "Depends(require_api_key)" not in content:
        failures.append("audit app endpoints missing require_api_key dependency")

    return failures


def validate_init_scripts() -> list[str]:
    failures: list[str] = []
    for script in INIT_SCRIPTS:
        content = script.read_text()
        if "set -Eeuo pipefail" not in content:
            failures.append(f"{script}: strict shell mode missing")
        if "for _ in $(seq" not in content:
            failures.append(f"{script}: bounded health wait loop missing")
        if "idempotent" not in content:
            failures.append(f"{script}: webhook idempotent marker missing")
    return failures


def main() -> int:
    failures = validate_audit_routes() + validate_init_scripts()
    if failures:
        print("Runtime contract validation failures:")
        print("\n".join(failures))
        return 1
    print("Runtime contract checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
