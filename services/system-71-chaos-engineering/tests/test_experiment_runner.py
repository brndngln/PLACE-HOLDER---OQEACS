from __future__ import annotations

from src.models import ChaosExperiment
from src.services.experiment_runner import ExperimentRunner


def _exp(ftype: str) -> ChaosExperiment:
    return ChaosExperiment(id="1", name="e", target_service="svc", failure_type=ftype, parameters={}, duration_seconds=10, steady_state_hypothesis="up")


def test_run_latency() -> None:
    res = ExperimentRunner().run(_exp("latency"))
    assert res.experiment_id == "1"


def test_run_error() -> None:
    res = ExperimentRunner().run(_exp("error"))
    assert isinstance(res.passed, bool)


def test_run_cpu() -> None:
    res = ExperimentRunner().run(_exp("cpu"))
    assert res.rollback_performed is True


def test_observations_present() -> None:
    res = ExperimentRunner().run(_exp("memory"))
    assert res.observations
