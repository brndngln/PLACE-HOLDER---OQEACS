from __future__ import annotations

from src.models import OptimizedPrompt, PromptOptimizeRequest


class PromptOptimizer:
    REDUNDANT_PHRASES = [
        "please carefully",
        "in a detailed manner",
        "very very",
        "strictly and absolutely",
    ]

    def optimize(self, request: PromptOptimizeRequest) -> OptimizedPrompt:
        original = request.current_prompt
        optimized = original
        for phrase in self.REDUNDANT_PHRASES:
            optimized = optimized.replace(phrase, "")
        optimized = " ".join(optimized.split())

        orig_tokens = max(1, len(original.split()))
        new_tokens = len(optimized.split())
        reduction = max(0.0, round(((orig_tokens - new_tokens) / orig_tokens) * 100, 2))

        quality = 0.85
        if request.optimization_goal == "quality":
            quality = 0.92
        elif request.optimization_goal == "speed":
            quality = 0.82

        return OptimizedPrompt(original=original, optimized=optimized, token_reduction_pct=reduction, quality_estimate=quality)
