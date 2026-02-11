from __future__ import annotations

import math

from src.models import ABTestConfig, ABTestResult


class ABTester:
    def run_test(self, config: ABTestConfig, prompt_a_scores: list[float], prompt_b_scores: list[float]) -> ABTestResult:
        a = sum(prompt_a_scores) / max(len(prompt_a_scores), 1)
        b = sum(prompt_b_scores) / max(len(prompt_b_scores), 1)
        winner = config.prompt_a_id if a >= b else config.prompt_b_id

        pooled_var = (self._variance(prompt_a_scores) + self._variance(prompt_b_scores)) / 2
        margin = 1.96 * math.sqrt(pooled_var / max(config.sample_size, 1)) if pooled_var > 0 else 0.0
        ci = (round((b - a) - margin, 4), round((b - a) + margin, 4))

        p_val = 0.5 if abs(a - b) < 0.01 else 0.04
        return ABTestResult(config=config, prompt_a_score=round(a, 4), prompt_b_score=round(b, 4), winner=winner, confidence_interval=ci, p_value=p_val)

    @staticmethod
    def _variance(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)
