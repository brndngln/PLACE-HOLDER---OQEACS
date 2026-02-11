from __future__ import annotations

from src.models import DecayReport


class DecayDetector:
    def check_decay(self, prompt_id: str, baseline_score: float, recent_scores: list[float]) -> DecayReport:
        current = sum(recent_scores) / max(len(recent_scores), 1)
        decay = 0.0 if baseline_score == 0 else ((baseline_score - current) / baseline_score) * 100
        if decay > 20:
            recommendation = "Re-optimize prompt and refresh few-shot examples"
        elif decay > 10:
            recommendation = "Run A/B test against latest best-performing version"
        else:
            recommendation = "No action needed"
        return DecayReport(prompt_id=prompt_id, current_score=round(current, 3), baseline_score=baseline_score, decay_pct=round(decay, 2), recommendation=recommendation)
