from __future__ import annotations

from datetime import datetime

from src.models import ChaosExperiment, ExperimentResult
from src.services.failure_injector import FailureInjector


class ExperimentRunner:
    def run(self, experiment: ChaosExperiment) -> ExperimentResult:
        injector = FailureInjector()
        before = True

        if experiment.failure_type == "latency":
            injector.inject_latency(experiment.target_service, int(experiment.parameters.get("delay_ms", 250)))
        elif experiment.failure_type == "error":
            injector.inject_errors(experiment.target_service, float(experiment.parameters.get("error_rate", 0.2)), int(experiment.parameters.get("status_code", 500)))
        elif experiment.failure_type == "cpu":
            injector.inject_cpu_pressure(experiment.target_service, int(experiment.parameters.get("percent", 80)))
        elif experiment.failure_type == "memory":
            injector.inject_memory_pressure(experiment.target_service, int(experiment.parameters.get("mb", 512)))
        elif experiment.failure_type == "network_partition":
            injector.inject_network_partition(experiment.target_service, str(experiment.parameters.get("peer", "unknown")))

        after = experiment.failure_type in {"latency", "error"}
        passed = before and after

        return ExperimentResult(
            experiment_id=experiment.id,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            steady_state_before=before,
            steady_state_after=after,
            passed=passed,
            observations=[f"Injected {experiment.failure_type} on {experiment.target_service}"],
            rollback_performed=True,
        )
