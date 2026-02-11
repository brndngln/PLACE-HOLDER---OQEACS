from __future__ import annotations

from src.services.failure_injector import FailureInjector


def test_inject_latency() -> None:
    out = FailureInjector().inject_latency("svc", 100)
    assert out["action"] == "latency"


def test_inject_errors() -> None:
    out = FailureInjector().inject_errors("svc", 0.2, 500)
    assert out["status_code"] == 500


def test_inject_cpu() -> None:
    out = FailureInjector().inject_cpu_pressure("svc", 80)
    assert out["percent"] == 80


def test_network_partition() -> None:
    out = FailureInjector().inject_network_partition("a", "b")
    assert out["action"] == "network_partition"
