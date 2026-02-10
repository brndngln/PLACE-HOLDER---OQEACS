from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

COMPOSE_FILES = [
    Path("omni-quantum-systems/system-45-email-service/docker-compose.yml"),
    Path("omni-quantum-systems/system-47-support-center/docker-compose.yml"),
    Path("omni-quantum-systems/system-48-web-analytics/docker-compose.yml"),
    Path("omni-quantum-systems/system-50-feature-flags/docker-compose.yml"),
    Path("omni-quantum-systems/system-51-error-tracking/docker-compose.yml"),
    Path("omni-quantum-systems/system-52-search-engine/docker-compose.yml"),
    Path("omni-quantum-systems/system-55-audit-logger/docker-compose.yml"),
    Path("omni-quantum-systems/system-58-translation-management/docker-compose.yml"),
]


def _expect(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def validate_compose(path: Path) -> list[str]:
    failures: list[str] = []
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict):
        return [f"{path}: not a valid yaml object"]

    networks = _as_dict(doc.get("networks"))
    omni_network = _as_dict(networks.get("omni-quantum-network"))
    _expect(omni_network.get("external") is True, f"{path}: omni-quantum-network must be external: true", failures)

    services = _as_dict(doc.get("services"))
    _expect(bool(services), f"{path}: services section missing", failures)

    for service_name, raw_service in services.items():
        service = _as_dict(raw_service)
        prefix = f"{path}:{service_name}"

        _expect(service.get("restart") == "unless-stopped", f"{prefix}: restart must be unless-stopped", failures)
        _expect("healthcheck" in service, f"{prefix}: healthcheck missing", failures)

        has_mem_limit = "mem_limit" in service
        has_deploy_limit = bool(_as_dict(_as_dict(service.get("deploy")).get("resources")).get("limits"))
        _expect(has_mem_limit or has_deploy_limit, f"{prefix}: resource limit missing", failures)

        logging_cfg = _as_dict(service.get("logging"))
        options = _as_dict(logging_cfg.get("options"))
        _expect(logging_cfg.get("driver") == "json-file", f"{prefix}: logging.driver must be json-file", failures)
        _expect(options.get("max-size") == "50m", f"{prefix}: logging max-size must be 50m", failures)
        _expect(str(options.get("max-file")) == "5", f"{prefix}: logging max-file must be 5", failures)

        labels = service.get("labels", {})
        label_map: dict[str, Any] = {}
        if isinstance(labels, dict):
            label_map = labels
        elif isinstance(labels, list):
            for entry in labels:
                if isinstance(entry, str) and "=" in entry:
                    key, value = entry.split("=", 1)
                    label_map[key] = value

        _expect("omni.quantum.component" in label_map, f"{prefix}: label omni.quantum.component missing", failures)
        _expect(str(label_map.get("omni.quantum.tier")) == "standard", f"{prefix}: label omni.quantum.tier must be standard", failures)
        _expect(str(label_map.get("omni.quantum.critical")).lower() == "false", f"{prefix}: label omni.quantum.critical must be false", failures)

        service_networks = service.get("networks", [])
        _expect(
            (isinstance(service_networks, list) and "omni-quantum-network" in service_networks)
            or (isinstance(service_networks, dict) and "omni-quantum-network" in service_networks),
            f"{prefix}: must attach omni-quantum-network",
            failures,
        )

    return failures


def main() -> int:
    failures: list[str] = []
    for compose in COMPOSE_FILES:
        failures.extend(validate_compose(compose))

    if failures:
        print("Compose conformance failures:")
        print("\n".join(failures))
        return 1

    print("Compose conformance OK for all 8 systems (semantic validation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
