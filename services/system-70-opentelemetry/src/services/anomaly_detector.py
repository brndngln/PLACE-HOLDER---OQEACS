from __future__ import annotations

from statistics import mean, pstdev


class AnomalyDetector:
    def detect_latency_anomalies(self, values: list[float], z_threshold: float = 2.5) -> list[dict]:
        if len(values) < 5:
            return []
        mu = mean(values)
        sigma = pstdev(values) or 1e-6
        out = []
        for i, v in enumerate(values):
            z = (v - mu) / sigma
            if abs(z) >= z_threshold:
                out.append({"index": i, "value": v, "z_score": round(z, 3), "type": "latency_spike" if v > mu else "latency_drop"})
        return out

    def detect_error_rate_increase(self, rates: list[float], threshold: float = 0.1) -> bool:
        if len(rates) < 2:
            return False
        return (rates[-1] - rates[0]) >= threshold
