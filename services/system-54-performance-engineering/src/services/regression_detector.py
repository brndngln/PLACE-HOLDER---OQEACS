from __future__ import annotations

from src.models import PerformanceRegression


class RegressionDetector:
    def detect_regressions(self, current_metrics: dict[str, float], baseline_metrics: dict[str, float]) -> list[PerformanceRegression]:
        out: list[PerformanceRegression] = []
        for metric, current in current_metrics.items():
            base = baseline_metrics.get(metric)
            if base is None or base == 0:
                continue
            pct = ((current - base) / base) * 100.0
            if pct > 20:
                severity = "high" if pct > 50 else "medium"
                out.append(PerformanceRegression(metric=metric, baseline=base, current=current, regression_pct=round(pct, 2), severity=severity))
        return out
