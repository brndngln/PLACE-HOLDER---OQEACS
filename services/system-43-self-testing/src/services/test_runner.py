"""
System 43 — TestRunner: the core engine that executes health checks and
integration tests against all Omni Quantum platform services.

The SERVICE_REGISTRY is the single source of truth for every monitored
service.  Health checks are run in parallel via ``asyncio.gather``;
integration tests are executed sequentially to avoid overwhelming
downstream services.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog
from prometheus_client import Counter, Histogram

from src.config import Settings
from src.models import (
    PlatformHealthReport,
    RunSuiteRequest,
    ServiceInfo,
    ServiceStatus,
    ServiceTarget,
    TestCase,
    TestResult,
    TestSuiteResult,
    TestType,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# -- Prometheus metrics -------------------------------------------------------

TESTS_EXECUTED = Counter(
    "self_test_executions_total",
    "Total individual test executions",
    ["target_service", "test_type", "passed"],
)
SUITE_RUNS = Counter(
    "self_test_suite_runs_total",
    "Total suite runs",
    ["suite_name"],
)
TEST_LATENCY = Histogram(
    "self_test_latency_seconds",
    "Test execution latency",
    ["target_service"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# -- Service registry ---------------------------------------------------------

SERVICE_REGISTRY: dict[str, ServiceTarget] = {
    "omni-postgres": ServiceTarget(
        name="omni-postgres",
        url="http://omni-postgres:5432",
        health_endpoint="/",
        expected_status=200,
    ),
    "omni-redis": ServiceTarget(
        name="omni-redis",
        url="http://omni-redis:6379",
        health_endpoint="/",
        expected_status=200,
    ),
    "omni-qdrant": ServiceTarget(
        name="omni-qdrant",
        url="http://omni-qdrant:6333",
        health_endpoint="/healthz",
        expected_status=200,
    ),
    "omni-litellm": ServiceTarget(
        name="omni-litellm",
        url="http://omni-litellm:4000",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-prometheus": ServiceTarget(
        name="omni-prometheus",
        url="http://omni-prometheus:9090",
        health_endpoint="/-/healthy",
        expected_status=200,
    ),
    "omni-grafana": ServiceTarget(
        name="omni-grafana",
        url="http://omni-grafana:3000",
        health_endpoint="/api/health",
        expected_status=200,
    ),
    "omni-loki": ServiceTarget(
        name="omni-loki",
        url="http://omni-loki:3100",
        health_endpoint="/ready",
        expected_status=200,
    ),
    "omni-mattermost": ServiceTarget(
        name="omni-mattermost",
        url="http://omni-mattermost:8065",
        health_endpoint="/api/v4/system/ping",
        expected_status=200,
    ),
    "omni-vault": ServiceTarget(
        name="omni-vault",
        url="http://omni-vault:8200",
        health_endpoint="/v1/sys/health",
        expected_status=200,
    ),
    "omni-gitea": ServiceTarget(
        name="omni-gitea",
        url="http://omni-gitea:3000",
        health_endpoint="/api/healthz",
        expected_status=200,
    ),
    "omni-n8n": ServiceTarget(
        name="omni-n8n",
        url="http://omni-n8n:5678",
        health_endpoint="/healthz",
        expected_status=200,
    ),
    "omni-langfuse": ServiceTarget(
        name="omni-langfuse",
        url="http://omni-langfuse:3000",
        health_endpoint="/api/public/health",
        expected_status=200,
    ),
    "omni-traefik": ServiceTarget(
        name="omni-traefik",
        url="http://omni-traefik:8080",
        health_endpoint="/ping",
        expected_status=200,
    ),
    "omni-orchestrator": ServiceTarget(
        name="omni-orchestrator",
        url="http://omni-orchestrator:9637",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-context-compiler": ServiceTarget(
        name="omni-context-compiler",
        url="http://omni-context-compiler:8100",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-freshness": ServiceTarget(
        name="omni-freshness",
        url="http://omni-freshness:8200",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-agent-health": ServiceTarget(
        name="omni-agent-health",
        url="http://omni-agent-health:9635",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-formal-verify": ServiceTarget(
        name="omni-formal-verify",
        url="http://omni-formal-verify:9634",
        health_endpoint="/health",
        expected_status=200,
    ),
    "omni-minio": ServiceTarget(
        name="omni-minio",
        url="http://omni-minio:9000",
        health_endpoint="/minio/health/live",
        expected_status=200,
    ),
    "omni-ollama": ServiceTarget(
        name="omni-ollama",
        url="http://omni-ollama:11434",
        health_endpoint="/api/tags",
        expected_status=200,
    ),
}

# -- Integration test definitions ---------------------------------------------

INTEGRATION_TESTS: list[TestCase] = [
    TestCase(
        name="context-compiler-compile",
        target_service="omni-context-compiler",
        test_type=TestType.INTEGRATION,
        request_method="POST",
        request_path="/api/v1/compile",
        request_body={
            "repo_url": "https://github.com/example/test-repo",
            "scope": "summary",
        },
        expected_status=200,
        expected_body_contains="context",
        timeout_seconds=15.0,
    ),
    TestCase(
        name="freshness-feeds-list",
        target_service="omni-freshness",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/feeds",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="agent-health-summary",
        target_service="omni-agent-health",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/agents",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="formal-verify-health",
        target_service="omni-formal-verify",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/verifications",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="orchestrator-services-list",
        target_service="omni-orchestrator",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/services",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="litellm-models-list",
        target_service="omni-litellm",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/v1/models",
        expected_status=200,
        expected_body_contains="data",
        timeout_seconds=10.0,
    ),
    TestCase(
        name="grafana-datasources",
        target_service="omni-grafana",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/datasources",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="prometheus-targets",
        target_service="omni-prometheus",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/targets",
        expected_status=200,
        expected_body_contains="activeTargets",
        timeout_seconds=10.0,
    ),
    TestCase(
        name="loki-ready-check",
        target_service="omni-loki",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/loki/api/v1/labels",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="minio-bucket-list",
        target_service="omni-minio",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/minio/health/cluster",
        expected_status=200,
        timeout_seconds=10.0,
    ),
    TestCase(
        name="vault-seal-status",
        target_service="omni-vault",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/v1/sys/seal-status",
        expected_status=200,
        expected_body_contains="sealed",
        timeout_seconds=10.0,
    ),
    TestCase(
        name="n8n-workflows-list",
        target_service="omni-n8n",
        test_type=TestType.INTEGRATION,
        request_method="GET",
        request_path="/api/v1/workflows",
        expected_status=200,
        timeout_seconds=10.0,
    ),
]


class TestRunner:
    """Executes tests against Omni Quantum platform services.

    Parameters
    ----------
    settings:
        Application settings (injected).
    redis_client:
        Async Redis connection for caching latest results.
    """

    def __init__(
        self,
        settings: Settings,
        redis_client: aioredis.Redis | None = None,
    ) -> None:
        self._settings = settings
        self._redis = redis_client
        self._latest_health: TestSuiteResult | None = None
        self._latest_integration: TestSuiteResult | None = None
        self._latest_report: PlatformHealthReport | None = None
        self._service_status: dict[str, ServiceInfo] = {}

    # -- public properties ----------------------------------------------------

    @property
    def latest_health_result(self) -> TestSuiteResult | None:
        return self._latest_health

    @property
    def latest_integration_result(self) -> TestSuiteResult | None:
        return self._latest_integration

    @property
    def latest_report(self) -> PlatformHealthReport | None:
        return self._latest_report

    @property
    def service_status_map(self) -> dict[str, ServiceInfo]:
        return dict(self._service_status)

    # -- single test execution ------------------------------------------------

    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Execute a single ``TestCase`` and return its ``TestResult``.

        Handles timeout, connection errors, status-code mismatches, and
        optional body-content assertions.
        """
        target = SERVICE_REGISTRY.get(test_case.target_service)
        if target is None:
            return TestResult(
                test_case_id=test_case.id,
                passed=False,
                error=f"Unknown service: {test_case.target_service}",
            )

        base_url = target.url
        url = f"{base_url}{test_case.request_path}"
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=test_case.timeout_seconds
            ) as client:
                if test_case.request_method.upper() == "GET":
                    response = await client.get(url)
                elif test_case.request_method.upper() == "POST":
                    response = await client.post(url, json=test_case.request_body)
                elif test_case.request_method.upper() == "PUT":
                    response = await client.put(url, json=test_case.request_body)
                elif test_case.request_method.upper() == "PATCH":
                    response = await client.patch(url, json=test_case.request_body)
                elif test_case.request_method.upper() == "DELETE":
                    response = await client.delete(url)
                else:
                    return TestResult(
                        test_case_id=test_case.id,
                        passed=False,
                        error=f"Unsupported method: {test_case.request_method}",
                    )

            elapsed_ms = (time.monotonic() - start) * 1000
            body_text = response.text[:500]

            # Check status code
            status_ok = response.status_code == test_case.expected_status

            # Check body contains (if specified)
            body_ok = True
            if test_case.expected_body_contains:
                body_ok = test_case.expected_body_contains in response.text

            passed = status_ok and body_ok
            error_msg: str | None = None
            if not status_ok:
                error_msg = (
                    f"Expected status {test_case.expected_status}, "
                    f"got {response.status_code}"
                )
            elif not body_ok:
                error_msg = (
                    f"Response body missing expected substring: "
                    f"'{test_case.expected_body_contains}'"
                )

            TESTS_EXECUTED.labels(
                target_service=test_case.target_service,
                test_type=test_case.test_type.value,
                passed=str(passed).lower(),
            ).inc()
            TEST_LATENCY.labels(
                target_service=test_case.target_service,
            ).observe(elapsed_ms / 1000)

            return TestResult(
                test_case_id=test_case.id,
                passed=passed,
                status_code=response.status_code,
                response_time_ms=round(elapsed_ms, 2),
                response_body_snippet=body_text,
                error=error_msg,
            )

        except httpx.TimeoutException:
            elapsed_ms = (time.monotonic() - start) * 1000
            TESTS_EXECUTED.labels(
                target_service=test_case.target_service,
                test_type=test_case.test_type.value,
                passed="false",
            ).inc()
            return TestResult(
                test_case_id=test_case.id,
                passed=False,
                response_time_ms=round(elapsed_ms, 2),
                error=f"Timeout after {test_case.timeout_seconds}s",
            )

        except httpx.ConnectError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            TESTS_EXECUTED.labels(
                target_service=test_case.target_service,
                test_type=test_case.test_type.value,
                passed="false",
            ).inc()
            return TestResult(
                test_case_id=test_case.id,
                passed=False,
                response_time_ms=round(elapsed_ms, 2),
                error=f"Connection refused: {exc}",
            )

        except httpx.RequestError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            TESTS_EXECUTED.labels(
                target_service=test_case.target_service,
                test_type=test_case.test_type.value,
                passed="false",
            ).inc()
            return TestResult(
                test_case_id=test_case.id,
                passed=False,
                response_time_ms=round(elapsed_ms, 2),
                error=f"Request error: {exc}",
            )

    # -- health check suite ---------------------------------------------------

    async def run_health_checks(
        self,
        services: list[str] | None = None,
    ) -> TestSuiteResult:
        """Run parallel health checks against all (or selected) services.

        Returns a ``TestSuiteResult`` with one ``TestResult`` per service.
        """
        started_at = datetime.now(timezone.utc)
        start_mono = time.monotonic()

        targets = SERVICE_REGISTRY
        if services:
            targets = {k: v for k, v in SERVICE_REGISTRY.items() if k in services}

        # Build a TestCase for every service health endpoint
        cases: list[TestCase] = [
            TestCase(
                name=f"health-{svc.name}",
                target_service=svc.name,
                test_type=TestType.HEALTH,
                request_method="GET",
                request_path=svc.health_endpoint,
                expected_status=svc.expected_status,
                timeout_seconds=8.0,
            )
            for svc in targets.values()
        ]

        # Execute in parallel
        results: list[TestResult] = await asyncio.gather(
            *(self.run_single_test(tc) for tc in cases)
        )

        elapsed_ms = (time.monotonic() - start_mono) * 1000
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and r.error and "error" not in r.error.lower())
        errors = sum(1 for r in results if not r.passed and r.error and "error" in r.error.lower())
        # Simplify: non-passed is either failed or error
        actual_failed = len(results) - passed

        suite = TestSuiteResult(
            suite_name="health-checks",
            total=len(results),
            passed=passed,
            failed=actual_failed,
            errors=0,
            results=results,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            duration_ms=round(elapsed_ms, 2),
        )

        SUITE_RUNS.labels(suite_name="health-checks").inc()
        self._latest_health = suite

        # Update per-service status cache
        for tc, result in zip(cases, results, strict=True):
            now = datetime.now(timezone.utc)
            svc_target = SERVICE_REGISTRY[tc.target_service]
            status = ServiceStatus.HEALTHY if result.passed else ServiceStatus.DOWN
            if result.status_code and result.status_code != svc_target.expected_status:
                status = ServiceStatus.DEGRADED
            if not result.passed and result.error and "Timeout" in result.error:
                status = ServiceStatus.DEGRADED

            self._service_status[tc.target_service] = ServiceInfo(
                name=svc_target.name,
                url=svc_target.url,
                health_endpoint=svc_target.health_endpoint,
                expected_status=svc_target.expected_status,
                last_status=status,
                last_checked=now,
                last_response_ms=result.response_time_ms,
            )

        # Cache in Redis
        await self._cache_result("self-test:health:latest", suite)

        logger.info(
            "health_checks_complete",
            total=suite.total,
            passed=suite.passed,
            failed=suite.failed,
            duration_ms=suite.duration_ms,
        )
        return suite

    # -- integration test suite -----------------------------------------------

    async def run_integration_suite(
        self,
        services: list[str] | None = None,
    ) -> TestSuiteResult:
        """Run the predefined integration tests sequentially.

        Parameters
        ----------
        services:
            If provided, only tests targeting these services will run.
        """
        started_at = datetime.now(timezone.utc)
        start_mono = time.monotonic()

        cases = INTEGRATION_TESTS
        if services:
            cases = [tc for tc in INTEGRATION_TESTS if tc.target_service in services]

        results: list[TestResult] = []
        for tc in cases:
            result = await self.run_single_test(tc)
            results.append(result)
            logger.debug(
                "integration_test_result",
                test=tc.name,
                passed=result.passed,
                ms=result.response_time_ms,
            )

        elapsed_ms = (time.monotonic() - start_mono) * 1000
        passed = sum(1 for r in results if r.passed)

        suite = TestSuiteResult(
            suite_name="integration-suite",
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            errors=0,
            results=results,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            duration_ms=round(elapsed_ms, 2),
        )

        SUITE_RUNS.labels(suite_name="integration-suite").inc()
        self._latest_integration = suite

        await self._cache_result("self-test:integration:latest", suite)

        logger.info(
            "integration_suite_complete",
            total=suite.total,
            passed=suite.passed,
            failed=suite.failed,
            duration_ms=suite.duration_ms,
        )
        return suite

    # -- full suite (health + integration) ------------------------------------

    async def run_full_suite(
        self,
        request: RunSuiteRequest | None = None,
    ) -> PlatformHealthReport:
        """Run health checks and integration tests, then produce a report."""
        services = request.services if request else None

        health_suite = await self.run_health_checks(services=services)
        integration_suite = await self.run_integration_suite(services=services)

        healthy = sum(
            1
            for info in self._service_status.values()
            if info.last_status == ServiceStatus.HEALTHY
        )
        degraded = sum(
            1
            for info in self._service_status.values()
            if info.last_status == ServiceStatus.DEGRADED
        )
        down = sum(
            1
            for info in self._service_status.values()
            if info.last_status == ServiceStatus.DOWN
        )

        total_tests = health_suite.total + integration_suite.total
        total_passed = health_suite.passed + integration_suite.passed
        score = round((total_passed / total_tests * 100) if total_tests > 0 else 0.0, 2)

        overall = ServiceStatus.HEALTHY
        if degraded > 0:
            overall = ServiceStatus.DEGRADED
        if down > 2:
            overall = ServiceStatus.DOWN

        report = PlatformHealthReport(
            services_tested=len(self._service_status),
            services_healthy=healthy,
            services_degraded=degraded,
            services_down=down,
            overall_status=overall,
            suite_results=[health_suite, integration_suite],
            score=score,
        )

        self._latest_report = report

        await self._cache_result("self-test:report:latest", report)

        # Optionally submit score to scoring service
        await self._submit_score(report)

        logger.info(
            "platform_report_generated",
            score=report.score,
            healthy=report.services_healthy,
            degraded=report.services_degraded,
            down=report.services_down,
        )
        return report

    # -- scoring integration --------------------------------------------------

    async def _submit_score(self, report: PlatformHealthReport) -> None:
        """Submit platform health score to GI-4 Quality Scoring."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self._settings.SCORING_URL}/api/v1/scores",
                    json={
                        "source": "self-testing",
                        "metric": "platform_health",
                        "score": report.score,
                        "details": {
                            "services_tested": report.services_tested,
                            "services_healthy": report.services_healthy,
                            "services_degraded": report.services_degraded,
                            "services_down": report.services_down,
                        },
                    },
                )
                logger.info("score_submitted", score=report.score)
        except httpx.RequestError as exc:
            logger.warning("score_submit_failed", error=str(exc))

    # -- redis caching --------------------------------------------------------

    async def _cache_result(self, key: str, data: Any) -> None:
        """Store a Pydantic model in Redis with a 24-hour TTL."""
        if self._redis is None:
            return
        try:
            payload = data.model_dump_json()
            await self._redis.set(key, payload, ex=86400)
        except Exception as exc:
            logger.warning("redis_cache_error", key=key, error=str(exc))

    async def get_cached_result(self, key: str) -> str | None:
        """Retrieve a cached JSON string from Redis."""
        if self._redis is None:
            return None
        try:
            return await self._redis.get(key)
        except Exception as exc:
            logger.warning("redis_get_error", key=key, error=str(exc))
            return None

    # -- service info ---------------------------------------------------------

    def list_services(self) -> list[ServiceInfo]:
        """Return the list of all monitored services with their last-known status."""
        result: list[ServiceInfo] = []
        for name, target in SERVICE_REGISTRY.items():
            if name in self._service_status:
                result.append(self._service_status[name])
            else:
                result.append(
                    ServiceInfo(
                        name=target.name,
                        url=target.url,
                        health_endpoint=target.health_endpoint,
                        expected_status=target.expected_status,
                    )
                )
        return result
