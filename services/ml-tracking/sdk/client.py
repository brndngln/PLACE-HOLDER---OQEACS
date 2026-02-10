"""ML Tracking SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class MLTrackingClient:
    def __init__(self, base_url: str = "http://localhost:5001"):
        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    def track_code_generation(self, model_name: str, quality_score: float, task_type: str, **kwargs: Any) -> str:
        payload = {"model_name": model_name, "quality_score": quality_score, "task_type": task_type, **kwargs}
        return self._post("/track/code-generation", payload)["run_id"]

    def track_code_review(self, reviewer_model: str, ai_score: float, human_score: float | None = None, **kwargs: Any) -> str:
        payload = {"reviewer_model": reviewer_model, "ai_score": ai_score, "human_score": human_score, **kwargs}
        return self._post("/track/code-review", payload)["run_id"]

    def track_model_comparison(self, model_a: str, model_b: str, scores_a: float, scores_b: float, **kwargs: Any) -> str:
        payload = {"model_a": model_a, "model_b": model_b, "model_a_score": scores_a, "model_b_score": scores_b, **kwargs}
        return self._post("/track/model-comparison", payload)["run_id"]

    def track_context_effectiveness(self, context_blocks: list[str], quality_score: float, **kwargs: Any) -> str:
        payload = {"context_blocks_included": context_blocks, "quality_score_with_context": quality_score, **kwargs}
        return self._post("/track/context-effectiveness", payload)["run_id"]

    def get_leaderboard(self) -> dict[str, Any]:
        return self._get("/leaderboard")

    def get_regressions(self) -> list[dict[str, Any]]:
        return self._get("/regressions").get("regressions", [])

    def get_experiment_summary(self, name: str) -> dict[str, Any]:
        return self._get(f"/experiments/{name}/summary")
