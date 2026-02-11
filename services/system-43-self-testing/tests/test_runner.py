"""
System 43 — TestRunner unit tests.

Validates the service registry completeness, TestCase model construction,
and single-test execution logic (mocked HTTP).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.models import ServiceStatus, TestCase, TestResult, TestType
from src.services.test_runner import (
    INTEGRATION_TESTS,
    SERVICE_REGISTRY,
    TestRunner,
)


# -- Service registry tests ---------------------------------------------------


class TestServiceRegistry:
    """Verify SERVICE_REGISTRY is complete and well-formed."""

    EXPECTED_SERVICES = [
        "omni-postgres",
        "omni-redis",
        "omni-qdrant",
        "omni-litellm",
        "omni-prometheus",
        "omni-grafana",
        "omni-loki",
        "omni-mattermost",
        "omni-vault",
        "omni-gitea",
        "omni-n8n",
        "omni-langfuse",
        "omni-traefik",
        "omni-orchestrator",
        "omni-context-compiler",
        "omni-freshness",
        "omni-agent-health",
        "omni-formal-verify",
        "omni-minio",
        "omni-ollama",
    ]

    def test_registry_has_at_least_20_services(self) -> None:
        assert len(SERVICE_REGISTRY) >= 20

    def test_all_expected_services_present(self) -> None:
        for svc in self.EXPECTED_SERVICES:
            assert svc in SERVICE_REGISTRY, f"Missing service: {svc}"

    def test_every_target_has_url(self) -> None:
        for name, target in SERVICE_REGISTRY.items():
            assert target.url, f"{name} has an empty URL"
            assert target.url.startswith("http"), f"{name} URL must start with http"

    def test_every_target_has_health_endpoint(self) -> None:
        for name, target in SERVICE_REGISTRY.items():
            assert target.health_endpoint, f"{name} has no health_endpoint"
            assert target.health_endpoint.startswith("/"), (
                f"{name} health_endpoint must start with /"
            )

    def test_every_target_has_valid_expected_status(self) -> None:
        for name, target in SERVICE_REGISTRY.items():
            assert 100 <= target.expected_status <= 599, (
                f"{name} has invalid expected_status: {target.expected_status}"
            )


# -- TestCase model tests ------------------------------------------------------


class TestTestCaseModel:
    """Verify TestCase Pydantic model behavior."""

    def test_default_values(self) -> None:
        tc = TestCase(name="example", target_service="omni-redis")
        assert tc.test_type == TestType.HEALTH
        assert tc.request_method == "GET"
        assert tc.request_path == "/health"
        assert tc.expected_status == 200
        assert tc.timeout_seconds == 10.0

    def test_custom_post_case(self) -> None:
        tc = TestCase(
            name="post-test",
            target_service="omni-context-compiler",
            test_type=TestType.INTEGRATION,
            request_method="POST",
            request_path="/api/v1/compile",
            request_body={"repo_url": "https://example.com"},
            expected_status=200,
            expected_body_contains="context",
            timeout_seconds=15.0,
        )
        assert tc.request_method == "POST"
        assert tc.request_body is not None
        assert tc.expected_body_contains == "context"

    def test_id_auto_generated(self) -> None:
        tc1 = TestCase(name="a", target_service="omni-redis")
        tc2 = TestCase(name="b", target_service="omni-redis")
        assert tc1.id != tc2.id
        assert len(tc1.id) == 12


# -- Integration test definitions ---------------------------------------------


class TestIntegrationTestDefinitions:
    """Verify the pre-defined INTEGRATION_TESTS list."""

    def test_at_least_10_integration_tests(self) -> None:
        assert len(INTEGRATION_TESTS) >= 10

    def test_all_targets_in_registry(self) -> None:
        for tc in INTEGRATION_TESTS:
            assert tc.target_service in SERVICE_REGISTRY, (
                f"Integration test '{tc.name}' references unknown service "
                f"'{tc.target_service}'"
            )

    def test_all_have_names(self) -> None:
        for tc in INTEGRATION_TESTS:
            assert tc.name, "Integration test missing a name"

    def test_all_are_integration_type(self) -> None:
        for tc in INTEGRATION_TESTS:
            assert tc.test_type == TestType.INTEGRATION


# -- TestRunner.run_single_test ------------------------------------------------


class TestRunSingleTest:
    """Test the run_single_test method with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_successful_get(self, runner: TestRunner) -> None:
        mock_response = httpx.Response(
            200,
            text='{"status":"ok"}',
            request=httpx.Request("GET", "http://omni-redis:6379/"),
        )
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-redis-health",
                target_service="omni-redis",
                request_path="/",
            )
            result = await runner.run_single_test(tc)

            assert isinstance(result, TestResult)
            assert result.passed is True
            assert result.status_code == 200
            assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_status_mismatch(self, runner: TestRunner) -> None:
        mock_response = httpx.Response(
            503,
            text="Service Unavailable",
            request=httpx.Request("GET", "http://omni-redis:6379/"),
        )
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-redis-fail",
                target_service="omni-redis",
                request_path="/",
                expected_status=200,
            )
            result = await runner.run_single_test(tc)

            assert result.passed is False
            assert result.status_code == 503
            assert "Expected status 200" in (result.error or "")

    @pytest.mark.asyncio
    async def test_body_contains_check(self, runner: TestRunner) -> None:
        mock_response = httpx.Response(
            200,
            text='{"data": []}',
            request=httpx.Request("GET", "http://omni-litellm:4000/v1/models"),
        )
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-litellm-models",
                target_service="omni-litellm",
                request_path="/v1/models",
                expected_body_contains="data",
            )
            result = await runner.run_single_test(tc)
            assert result.passed is True

    @pytest.mark.asyncio
    async def test_body_contains_failure(self, runner: TestRunner) -> None:
        mock_response = httpx.Response(
            200,
            text='{"result": "ok"}',
            request=httpx.Request("GET", "http://omni-litellm:4000/v1/models"),
        )
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-litellm-missing",
                target_service="omni-litellm",
                request_path="/v1/models",
                expected_body_contains="nonexistent_key",
            )
            result = await runner.run_single_test(tc)
            assert result.passed is False
            assert "missing expected substring" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_unknown_service(self, runner: TestRunner) -> None:
        tc = TestCase(
            name="test-unknown",
            target_service="omni-nonexistent",
            request_path="/health",
        )
        result = await runner.run_single_test(tc)
        assert result.passed is False
        assert "Unknown service" in (result.error or "")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, runner: TestRunner) -> None:
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-timeout",
                target_service="omni-redis",
                request_path="/",
                timeout_seconds=1.0,
            )
            result = await runner.run_single_test(tc)
            assert result.passed is False
            assert "Timeout" in (result.error or "")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, runner: TestRunner) -> None:
        with patch("src.services.test_runner.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            tc = TestCase(
                name="test-connect-error",
                target_service="omni-redis",
                request_path="/",
            )
            result = await runner.run_single_test(tc)
            assert result.passed is False
            assert "Connection refused" in (result.error or "")


# -- list_services ------------------------------------------------------------


class TestListServices:
    """Verify the service listing helper."""

    def test_returns_all_registered_services(self, runner: TestRunner) -> None:
        services = runner.list_services()
        assert len(services) == len(SERVICE_REGISTRY)
        names = {s.name for s in services}
        for svc_name in SERVICE_REGISTRY:
            assert svc_name in names
