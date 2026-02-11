"""
System 43 — Pydantic v2 data models.

Every model uses ``model_config = ConfigDict(from_attributes=True)`` so
ORM rows or plain dicts can be loaded with ``Model.model_validate()``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# -- Enums -------------------------------------------------------------------


class TestType(str, Enum):
    HEALTH = "health"
    INTEGRATION = "integration"
    SMOKE = "smoke"
    CONTRACT = "contract"


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


# -- Service target -----------------------------------------------------------


class ServiceTarget(BaseModel):
    """A service on the Omni Quantum network to be tested."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Human-readable service name")
    url: str = Field(..., description="Base URL of the service")
    health_endpoint: str = Field(
        default="/health",
        description="Path to the health-check endpoint",
    )
    expected_status: int = Field(
        default=200,
        description="Expected HTTP status code from the health endpoint",
    )


# -- Test case ----------------------------------------------------------------


class TestCase(BaseModel):
    """Definition of a single test to execute against a platform service."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=_new_id, description="Unique test-case ID")
    name: str = Field(..., description="Human-readable test name")
    target_service: str = Field(..., description="Name of the target service")
    test_type: TestType = Field(default=TestType.HEALTH)
    request_method: str = Field(default="GET", description="HTTP method")
    request_path: str = Field(default="/health", description="Request path")
    request_body: dict[str, Any] | None = Field(
        default=None, description="JSON body for POST/PUT/PATCH"
    )
    expected_status: int = Field(default=200)
    expected_body_contains: str | None = Field(
        default=None,
        description="Substring the response body must contain",
    )
    timeout_seconds: float = Field(default=10.0, gt=0)


# -- Test result --------------------------------------------------------------


class TestResult(BaseModel):
    """Outcome of a single executed test case."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=_new_id)
    test_case_id: str = Field(..., description="ID of the originating TestCase")
    passed: bool = Field(default=False)
    status_code: int | None = Field(
        default=None, description="HTTP status code received"
    )
    response_time_ms: float = Field(
        default=0.0, ge=0.0, description="Wall-clock latency in milliseconds"
    )
    response_body_snippet: str = Field(
        default="",
        description="First 500 chars of the response body for diagnostics",
    )
    error: str | None = Field(
        default=None, description="Error message if the test failed"
    )
    timestamp: datetime = Field(default_factory=_utcnow)


# -- Test suite result --------------------------------------------------------


class TestSuiteResult(BaseModel):
    """Aggregated outcome of running a collection of test cases."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=_new_id)
    suite_name: str = Field(..., description="Name of the suite that was run")
    total: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    results: list[TestResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = Field(default=None)
    duration_ms: float = Field(default=0.0, ge=0.0)


# -- Platform health report ---------------------------------------------------


class PlatformHealthReport(BaseModel):
    """Top-level platform health snapshot generated from suite results."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(default_factory=_utcnow)
    services_tested: int = Field(default=0, ge=0)
    services_healthy: int = Field(default=0, ge=0)
    services_degraded: int = Field(default=0, ge=0)
    services_down: int = Field(default=0, ge=0)
    overall_status: ServiceStatus = Field(default=ServiceStatus.UNKNOWN)
    suite_results: list[TestSuiteResult] = Field(default_factory=list)
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Platform health score 0-100",
    )


# -- API request / response helpers -------------------------------------------


class RunSuiteRequest(BaseModel):
    """Request body for triggering a custom suite run."""

    suite_name: str = Field(default="ad-hoc", description="Name tag for this run")
    services: list[str] | None = Field(
        default=None,
        description="Restrict to specific services; None = all",
    )
    include_integration: bool = Field(
        default=True,
        description="Include integration tests in addition to health checks",
    )


class ServiceInfo(BaseModel):
    """Read-only view of a monitored service."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    health_endpoint: str
    expected_status: int
    last_status: ServiceStatus = Field(default=ServiceStatus.UNKNOWN)
    last_checked: datetime | None = Field(default=None)
    last_response_ms: float | None = Field(default=None)
