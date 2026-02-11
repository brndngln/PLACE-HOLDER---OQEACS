#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       PROMPT DECAY DETECTION SERVICE                          ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice monitors the quality of generated code over time by        ║
║ running a golden test suite on a regular schedule and comparing the average  ║
║ scores against a baseline.  When the average falls below a configured       ║
║ threshold, it sends notifications via Mattermost and triggers a prompt       ║
║ refresh on the Omi wearable.  It exposes endpoints to trigger evaluations    ║
║ manually and integrates with the Omni event bus for alerting.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app


# ════════════════════════════════════════════════════════════════════
# DATA MODELS
# ════════════════════════════════════════════════════════════════════


class TestResult(BaseModel):
    name: str
    score: float
    details: Dict[str, any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    status: str
    average_score: float
    results: List[TestResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class PromptDecayDetector:
    """Service responsible for running golden tests and detecting prompt decay."""

    code_scorer_url: str
    mattermost_webhook: str
    omi_endpoint: str
    threshold: float
    golden_tests: List[dict]
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    request_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="prompt_decay_detector")
        self.request_counter = Counter(
            "prompt_decay_requests_total", "Total prompt decay runs"
        )
        self.latency_histogram = Histogram(
            "prompt_decay_latency_seconds",
            "Latency of prompt decay runs",
            buckets=(0.5, 1, 2, 5, 10, 30),
        )

    async def run_tests(self) -> RunResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            async with httpx.AsyncClient(timeout=10) as client:
                results: List[TestResult] = []
                for test in self.golden_tests:
                    # Send code to code scorer
                    try:
                        resp = await client.post(
                            f"{self.code_scorer_url}/api/v1/score",
                            json={"code": test["code"]},
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        score = data.get("weighted_average", 0.0)
                        results.append(TestResult(name=test["name"], score=score, details=data))
                    except Exception as exc:
                        self.logger.error("score_request_failed", test=test.get("name"), error=str(exc))
                        results.append(TestResult(name=test.get("name", "unknown"), score=0.0, details={"error": str(exc)}))
                if not results:
                    raise HTTPException(status_code=500, detail="No tests executed")
                average_score = sum(r.score for r in results) / len(results)
                if average_score < self.threshold:
                    await self._notify(average_score, results)
                return RunResponse(status="OK", average_score=average_score, results=results)

    async def _notify(self, avg_score: float, results: List[TestResult]) -> None:
        """Send alert to Mattermost and Omi when decay detected."""
        message = {
            "text": f"🚨 Prompt decay detected: average score {avg_score:.2f} below threshold {self.threshold}"}
        # Mattermost
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(self.mattermost_webhook, json=message)
        except Exception as exc:
            self.logger.warning("mattermost_notification_failed", error=str(exc))
        # Omi haptic or voice: send minimal payload
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(self.omi_endpoint, json={"event": "prompt_decay", "score": avg_score})
        except Exception as exc:
            self.logger.warning("omi_notification_failed", error=str(exc))

    async def schedule_loop(self) -> None:
        interval_hours = float(os.getenv("DECAY_INTERVAL_HOURS", "168"))
        interval = interval_hours * 3600
        while True:
            try:
                await self.run_tests()
            except Exception as exc:
                self.logger.error("scheduled_run_failed", error=str(exc))
            await asyncio.sleep(interval)


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def load_golden_tests() -> List[dict]:
    """Load golden test cases from an environment-defined location or fallback to defaults."""
    import json
    tests_path = os.getenv("GOLDEN_TESTS_FILE")
    if tests_path and os.path.isfile(tests_path):
        with open(tests_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    # Fallback: simple sample tests
    return [
        {"name": "test_simple_function", "code": "def add(a: int, b: int) -> int:\n    return a + b\n"},
        {"name": "test_class", "code": "class Foo:\n    def bar(self) -> int:\n        return 42\n"},
    ]


def create_app() -> FastAPI:
    code_scorer_url = os.getenv("CODE_SCORER_URL", "http://omni-code-scorer:8350")
    mattermost_webhook = os.getenv("MATTERMOST_WEBHOOK", "")
    omi_endpoint = os.getenv("OMI_ENDPOINT", "http://omni-omi-bridge:9700/api/v1/notify")
    threshold = float(os.getenv("DECAY_THRESHOLD", "8.0"))
    golden_tests = load_golden_tests()
    detector = PromptDecayDetector(code_scorer_url, mattermost_webhook, omi_endpoint, threshold, golden_tests)
    app = FastAPI(title="Prompt Decay Detector", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Start scheduler on startup
    @app.on_event("startup")
    async def startup_event() -> None:
        if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
            app.add_event_handler("startup", lambda: asyncio.create_task(detector.schedule_loop()))

    @app.post("/api/v1/run", response_model=RunResponse)
    async def run_endpoint(background_tasks: BackgroundTasks) -> RunResponse:
        # run tests and return immediate response; notifications handled in service
        return await detector.run_tests()

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Basic readiness: ensure code scorer is reachable
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(code_scorer_url + "/health")
                if resp.status_code != 200:
                    raise Exception("code scorer not healthy")
        except Exception:
            raise HTTPException(status_code=503, detail="Dependencies unavailable")
        return {"status": "ready"}

    return app


app = create_app()