from __future__ import annotations

import subprocess


def run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_compose_conformance_script() -> None:
    run(["python", "omni-quantum-systems/hardening/scripts/validate_compose_conformance.py"])


def test_sdk_conformance_script() -> None:
    run(["python", "omni-quantum-systems/hardening/scripts/validate_sdk_conformance.py"])


def test_runtime_contracts_script() -> None:
    run(["python", "omni-quantum-systems/hardening/scripts/validate_runtime_contracts.py"])
