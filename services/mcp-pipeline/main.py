#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         MCP PIPELINE TOOLS SERVICE                            ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice exposes endpoints for executing various pipeline tools      ║
║ during code generation: linting, static type checking, running unit tests,    ║
║ and performing security analysis.  Requests provide code snippets or paths,   ║
║ and the service spawns subprocesses to run the appropriate tools within      ║
║ isolated temporary directories.  Outputs are parsed and returned as JSON.     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app


# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class PipelineStatus(str):
    """Outcome status of pipeline tool execution."""

    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class RunCodeRequest(BaseModel):
    """Input model for code-based operations."""

    code: str = Field(..., description="Raw Python code to analyze")


class RunPathRequest(BaseModel):
    """Input model for path-based operations."""

    path: str = Field(..., description="Filesystem path containing code and tests")


class LintIssue(BaseModel):
    file: str
    line: int
    column: int
    code: str
    message: str


class LintResponse(BaseModel):
    status: PipelineStatus = Field(...)
    issues: List[LintIssue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TypeCheckIssue(BaseModel):
    file: str
    line: int
    message: str


class TypeCheckResponse(BaseModel):
    status: PipelineStatus = Field(...)
    issues: List[TypeCheckIssue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TestResult(BaseModel):
    passed: int
    failed: int
    errors: int
    skipped: int
    details: Optional[str] = None


class TestResponse(BaseModel):
    status: PipelineStatus = Field(...)
    result: TestResult
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityIssue(BaseModel):
    file: str
    line: int
    code: str
    message: str


class SecurityResponse(BaseModel):
    status: PipelineStatus = Field(...)
    issues: List[SecurityIssue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class PipelineService:
    """Service encapsulating pipeline operations."""

    logger: structlog.BoundLogger = dataclasses.field(init=False)
    request_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="pipeline_service")
        self.request_counter = Counter(
            "mcp_pipeline_requests_total", "Total pipeline requests"
        )
        self.latency_histogram = Histogram(
            "mcp_pipeline_latency_seconds",
            "Latency of pipeline operations",
            buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
        )

    async def run_linter(self, code: str) -> LintResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, "snippet.py")
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(code)
                cmd = ["ruff", "check", "--format=json", file_path]
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if proc.returncode not in (0, 1):
                        self.logger.error("ruff_error", stderr=stderr.decode())
                        raise HTTPException(status_code=500, detail="Linter execution failed")
                    import json

                    issues_data = json.loads(stdout.decode() or "[]")
                    issues: List[LintIssue] = []
                    for item in issues_data:
                        issues.append(
                            LintIssue(
                                file=item.get("filename", "snippet.py"),
                                line=item.get("location", {}).get("row", 0),
                                column=item.get("location", {}).get("column", 0),
                                code=item.get("code", ""),
                                message=item.get("message", ""),
                            )
                        )
                    status = PipelineStatus.FAIL if issues else PipelineStatus.SUCCESS
                    return LintResponse(status=status, issues=issues)
                except Exception as exc:
                    self.logger.error("linter_failed", error=str(exc))
                    return LintResponse(status=PipelineStatus.ERROR, issues=[])

    async def run_type_check(self, code: str) -> TypeCheckResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, "snippet.py")
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(code)
                # Initialize a minimal pyproject for pyright
                pyproject = os.path.join(tmpdir, "pyproject.toml")
                with open(pyproject, "w", encoding="utf-8") as fh:
                    fh.write("[tool.pyright]\ntypeCheckingMode = 'basic'\n")
                cmd = ["pyright", file_path, "--outputjson"]
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if proc.returncode not in (0, 1):
                        self.logger.error("pyright_error", stderr=stderr.decode())
                        raise HTTPException(status_code=500, detail="Type checker execution failed")
                    import json
                    result = json.loads(stdout.decode() or "{}")
                    diagnostics = result.get("generalDiagnostics", [])
                    issues: List[TypeCheckIssue] = []
                    for diag in diagnostics:
                        loc = diag.get("range", {}).get("start", {})
                        issues.append(
                            TypeCheckIssue(
                                file=diag.get("file", "snippet.py"),
                                line=loc.get("line", 0) + 1,
                                message=diag.get("message", ""),
                            )
                        )
                    status = PipelineStatus.FAIL if issues else PipelineStatus.SUCCESS
                    return TypeCheckResponse(status=status, issues=issues)
                except Exception as exc:
                    self.logger.error("type_check_failed", error=str(exc))
                    return TypeCheckResponse(status=PipelineStatus.ERROR, issues=[])

    async def run_unit_tests(self, path: str) -> TestResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            # Run pytest in the specified path
            if not os.path.isdir(path):
                return TestResponse(status=PipelineStatus.ERROR, result=TestResult(passed=0, failed=0, errors=0, skipped=0, details="Invalid path"))
            cmd = ["pytest", "-q", "--disable-warnings", "--maxfail=1"]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                output = stdout.decode()
                # Parse summary line (e.g., "2 passed, 1 failed in 0.03s")
                passed = failed = errors = skipped = 0
                for line in output.splitlines():
                    if "passed" in line or "failed" in line or "error" in line or "skipped" in line:
                        parts = [p.strip() for p in line.split(',')]
                        for part in parts:
                            if part.endswith("passed"):
                                passed = int(part.split()[0])
                            elif part.endswith("failed"):
                                failed = int(part.split()[0])
                            elif part.endswith("errors") or part.endswith("error"):
                                errors = int(part.split()[0])
                            elif part.endswith("skipped"):
                                skipped = int(part.split()[0])
                status = PipelineStatus.FAIL if failed or errors else PipelineStatus.SUCCESS
                return TestResponse(status=status, result=TestResult(passed=passed, failed=failed, errors=errors, skipped=skipped, details=output))
            except Exception as exc:
                self.logger.error("unit_tests_failed", error=str(exc))
                return TestResponse(status=PipelineStatus.ERROR, result=TestResult(passed=0, failed=0, errors=0, skipped=0, details=str(exc)))

    async def check_security(self, code: str) -> SecurityResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, "snippet.py")
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(code)
                cmd = ["bandit", "-f", "json", "-q", file_path]
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if proc.returncode not in (0, 1):
                        self.logger.error("bandit_error", stderr=stderr.decode())
                        raise HTTPException(status_code=500, detail="Security analysis failed")
                    import json
                    result = json.loads(stdout.decode() or "{}")
                    issues: List[SecurityIssue] = []
                    for item in result.get("results", []):
                        issues.append(
                            SecurityIssue(
                                file=item.get("filename", "snippet.py"),
                                line=item.get("line_number", 0),
                                code=item.get("test_id", ""),
                                message=item.get("issue_text", ""),
                            )
                        )
                    status = PipelineStatus.FAIL if issues else PipelineStatus.SUCCESS
                    return SecurityResponse(status=status, issues=issues)
                except Exception as exc:
                    self.logger.error("security_check_failed", error=str(exc))
                    return SecurityResponse(status=PipelineStatus.ERROR, issues=[])


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    service = PipelineService()
    app = FastAPI(title="MCP Pipeline", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/run_linter", response_model=LintResponse)
    async def run_linter_endpoint(request: RunCodeRequest) -> LintResponse:
        return await service.run_linter(request.code)

    @app.post("/api/v1/run_type_check", response_model=TypeCheckResponse)
    async def run_type_check_endpoint(request: RunCodeRequest) -> TypeCheckResponse:
        return await service.run_type_check(request.code)

    @app.post("/api/v1/run_unit_tests", response_model=TestResponse)
    async def run_unit_tests_endpoint(request: RunPathRequest) -> TestResponse:
        return await service.run_unit_tests(request.path)

    @app.post("/api/v1/check_security", response_model=SecurityResponse)
    async def check_security_endpoint(request: RunCodeRequest) -> SecurityResponse:
        return await service.check_security(request.code)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Quick smoke check: ensure required executables are available
        for cmd in ["ruff", "pyright", "pytest", "bandit"]:
            if shutil.which(cmd) is None:
                raise HTTPException(status_code=503, detail=f"{cmd} not installed")
        return {"status": "ready"}

    return app


app = create_app()