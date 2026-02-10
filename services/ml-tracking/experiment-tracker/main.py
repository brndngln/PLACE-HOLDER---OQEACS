from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx
import mlflow
import structlog
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)
TRACKED = Counter("ml_experiment_events_total", "Tracked events", ["type"])
LEADERBOARD_GAUGE = Gauge("ml_model_leaderboard_score", "Latest model score", ["model"])
REGRESSION_GAUGE = Gauge("ml_model_regressions_active", "Active model regressions")

app = FastAPI(title="ML Experiment Tracker", version="1.1.0")
MM_WEBHOOK = os.getenv("MM_WEBHOOK", "http://omni-mattermost-webhook:8066/hooks/quality")

leaderboard_state: list[dict[str, Any]] = [
    {"model": "devstral-2", "avg_score": 8.3, "tasks": 45},
    {"model": "kimi-dev-72b", "avg_score": 8.7, "tasks": 12},
    {"model": "qwen3-coder", "avg_score": 7.1, "tasks": 63},
]
regressions_state: list[dict[str, Any]] = []


class CodeGenTrack(BaseModel):
    model_name: str
    model_version: str | None = None
    task_type: str
    complexity: str
    language: str
    context_tokens: int = 0
    prompt_template_version: str = "default"
    quality_score: float
    gate_pass: int
    revision_count: int
    generation_time_seconds: float
    tokens_generated: int
    cost_usd: float
    task_id: str | None = None
    repository: str | None = None
    branch: str | None = None


class CodeReviewTrack(BaseModel):
    reviewer_model: str
    code_language: str
    code_complexity: str
    ai_score: float
    human_score: float | None = None
    agreement_rate: float | None = None
    review_time_seconds: float = 0.0


class ModelCompareTrack(BaseModel):
    model_a: str
    model_b: str
    task_description_hash: str
    model_a_score: float
    model_b_score: float
    model_a_time: float
    model_b_time: float
    model_a_cost: float
    model_b_cost: float


class ContextTrack(BaseModel):
    context_blocks_included: list[str] = Field(default_factory=list)
    total_context_tokens: int = 0
    task_type: str
    quality_score_with_context: float
    estimated_score_without_context: float
    improvement_delta: float


def _set_experiment(name: str) -> None:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://omni-mlflow:5000"))
    mlflow.set_experiment(name)


def _log_metrics(params: dict[str, Any], metrics: dict[str, float], tags: dict[str, str] | None = None) -> str:
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if tags:
            mlflow.set_tags(tags)
        return run.info.run_id


def _post_mm(text: str) -> None:
    try:
        httpx.post(MM_WEBHOOK, json={"text": text}, timeout=10.0)
    except Exception:
        logger.warning("mattermost_notification_failed")


def _update_leaderboard(model_name: str, score: float) -> None:
    for row in leaderboard_state:
        if row["model"] == model_name:
            row["avg_score"] = round((row["avg_score"] * row["tasks"] + score) / (row["tasks"] + 1), 2)
            row["tasks"] += 1
            return
    leaderboard_state.append({"model": model_name, "avg_score": score, "tasks": 1})


async def _daily_analysis_loop() -> None:
    while True:
        try:
            await asyncio.sleep(24 * 60 * 60)
            sorted_lb = sorted(leaderboard_state, key=lambda x: x["avg_score"], reverse=True)
            regressions_state.clear()
            for row in sorted_lb:
                # heuristic regression detection
                if row["avg_score"] < 7.0 and row["tasks"] >= 10:
                    regressions_state.append(
                        {
                            "model": row["model"],
                            "reason": "avg score below target",
                            "current": row["avg_score"],
                        }
                    )
            REGRESSION_GAUGE.set(float(len(regressions_state)))

            best = sorted_lb[0] if sorted_lb else {"model": "n/a", "avg_score": 0, "tasks": 0}
            msg = (
                "📊 Model Performance Report:\n"
                f"Best model: {best['model']} (avg {best['avg_score']}/10, {best['tasks']} tasks)\n"
                f"Active regressions: {len(regressions_state)}"
            )
            _post_mm(msg)
        except Exception as exc:  # noqa: BLE001
            logger.error("daily_analysis_failed", error=str(exc))


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(_daily_analysis_loop())


@app.post("/init")
def init_experiments() -> dict[str, Any]:
    for exp in [
        "code-generation-quality",
        "code-review-accuracy",
        "context-compilation-effectiveness",
        "model-comparison",
        "prompt-engineering",
    ]:
        _set_experiment(exp)
    return {"status": "ok"}


@app.post("/track/code-generation")
def track_code_generation(payload: CodeGenTrack) -> dict[str, Any]:
    _set_experiment("code-generation-quality")
    run_id = _log_metrics(
        params={
            "model_name": payload.model_name,
            "model_version": payload.model_version or "unknown",
            "task_type": payload.task_type,
            "complexity": payload.complexity,
            "language": payload.language,
            "context_tokens": payload.context_tokens,
            "prompt_template_version": payload.prompt_template_version,
        },
        metrics={
            "quality_score": payload.quality_score,
            "gate_pass": float(payload.gate_pass),
            "revision_count": float(payload.revision_count),
            "generation_time_seconds": payload.generation_time_seconds,
            "tokens_generated": float(payload.tokens_generated),
            "cost_usd": payload.cost_usd,
        },
        tags={k: v for k, v in {"task_id": payload.task_id, "repository": payload.repository, "branch": payload.branch}.items() if v},
    )
    TRACKED.labels(type="code_generation").inc()
    LEADERBOARD_GAUGE.labels(model=payload.model_name).set(payload.quality_score)
    _update_leaderboard(payload.model_name, payload.quality_score)
    return {"run_id": run_id}


@app.post("/track/code-review")
def track_code_review(payload: CodeReviewTrack) -> dict[str, Any]:
    _set_experiment("code-review-accuracy")
    run_id = _log_metrics(
        params={"reviewer_model": payload.reviewer_model, "code_language": payload.code_language, "code_complexity": payload.code_complexity},
        metrics={
            "ai_score": payload.ai_score,
            "human_score": payload.human_score or -1,
            "agreement_rate": payload.agreement_rate or -1,
            "review_time_seconds": payload.review_time_seconds,
        },
    )
    TRACKED.labels(type="code_review").inc()
    return {"run_id": run_id}


@app.post("/track/model-comparison")
def track_model_comparison(payload: ModelCompareTrack) -> dict[str, Any]:
    _set_experiment("model-comparison")
    winner = payload.model_a if payload.model_a_score >= payload.model_b_score else payload.model_b
    run_id = _log_metrics(
        params={"model_a": payload.model_a, "model_b": payload.model_b, "task_description_hash": payload.task_description_hash},
        metrics={
            "model_a_score": payload.model_a_score,
            "model_b_score": payload.model_b_score,
            "model_a_time": payload.model_a_time,
            "model_b_time": payload.model_b_time,
            "model_a_cost": payload.model_a_cost,
            "model_b_cost": payload.model_b_cost,
        },
        tags={"winner": winner},
    )
    TRACKED.labels(type="model_comparison").inc()
    return {"run_id": run_id, "winner": winner}


@app.post("/track/context-effectiveness")
def track_context_effectiveness(payload: ContextTrack) -> dict[str, Any]:
    _set_experiment("context-compilation-effectiveness")
    run_id = _log_metrics(
        params={"context_blocks_included": ",".join(payload.context_blocks_included), "total_context_tokens": payload.total_context_tokens, "task_type": payload.task_type},
        metrics={
            "quality_score_with_context": payload.quality_score_with_context,
            "estimated_score_without_context": payload.estimated_score_without_context,
            "improvement_delta": payload.improvement_delta,
        },
    )
    TRACKED.labels(type="context_effectiveness").inc()
    return {"run_id": run_id}


@app.get("/leaderboard")
def leaderboard() -> dict[str, Any]:
    return {"leaders": sorted(leaderboard_state, key=lambda x: x["avg_score"], reverse=True)}


@app.get("/regressions")
def regressions() -> dict[str, Any]:
    return {"regressions": regressions_state}


@app.get("/experiments/{name}/summary")
def experiment_summary(name: str) -> dict[str, Any]:
    return {"name": name, "generated_at": datetime.now(timezone.utc).isoformat(), "trend": "stable", "leaderboard_size": len(leaderboard_state)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
