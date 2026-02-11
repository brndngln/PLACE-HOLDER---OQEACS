from __future__ import annotations


class FailureInjector:
    def inject_latency(self, target: str, delay_ms: int) -> dict:
        return {"target": target, "action": "latency", "delay_ms": delay_ms}

    def inject_errors(self, target: str, error_rate: float, status_code: int) -> dict:
        return {"target": target, "action": "error", "error_rate": error_rate, "status_code": status_code}

    def inject_cpu_pressure(self, target: str, percent: int) -> dict:
        return {"target": target, "action": "cpu", "percent": percent}

    def inject_memory_pressure(self, target: str, mb: int) -> dict:
        return {"target": target, "action": "memory", "mb": mb}

    def inject_network_partition(self, target_a: str, target_b: str) -> dict:
        return {"target_a": target_a, "target_b": target_b, "action": "network_partition"}
