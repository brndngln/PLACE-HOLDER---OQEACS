from __future__ import annotations

import asyncio
import subprocess
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, model_validator

from app.config import settings

router = APIRouter()


class Language(str, Enum):
    PYTHON_312 = "python:3.12"
    PYTHON_311 = "python:3.11"
    NODE_22 = "node:22"
    NODE_20 = "node:20"
    GO_122 = "go:1.22"
    RUST_178 = "rust:1.78"
    JAVA_21 = "java:21"
    DOTNET_8 = "dotnet:8"
    RUBY_33 = "ruby:3.3"
    CPP_LATEST = "cpp:latest"
    ELIXIR_116 = "elixir:1.16"


class ExecutionType(str, Enum):
    SMOKE_RUN = "SMOKE_RUN"
    TEST_RUN = "TEST_RUN"
    IMPORT_CHECK = "IMPORT_CHECK"
    API_CHECK = "API_CHECK"
    BUILD_CHECK = "BUILD_CHECK"
    LINT_CHECK = "LINT_CHECK"
    TYPE_CHECK = "TYPE_CHECK"
    REPL = "REPL"
    CUSTOM = "CUSTOM"


class SandboxStatus(str, Enum):
    CREATING = "CREATING"
    INSTALLING_DEPS = "INSTALLING_DEPS"
    READY = "READY"
    EXECUTING = "EXECUTING"
    ERROR = "ERROR"
    DESTROYING = "DESTROYING"
    DESTROYED = "DESTROYED"


class CreateSandboxRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)
    language: Language
    dependencies: list[str] = Field(default_factory=list, max_length=200)
    workspace_files: dict[str, str] | None = None
    memory_limit: str | None = Field(default=None, pattern=r"^\d+[mg]$")
    cpu_limit: float | None = Field(default=None, ge=0.5, le=8.0)
    network_mode: str | None = "none"
    environment: dict[str, str] | None = None
    ttl_seconds: int | None = Field(default=None, ge=60, le=86400)

    @model_validator(mode="after")
    def _validate_inputs(self) -> "CreateSandboxRequest":
        blocked = set(";|&`$(){}")
        for dep in self.dependencies:
            if any(ch in dep for ch in blocked):
                raise ValueError("dependency contains blocked shell characters")
        if self.workspace_files:
            for path, content in self.workspace_files.items():
                if path.startswith("/") or ".." in path:
                    raise ValueError("workspace file path is invalid")
                if len(content.encode("utf-8")) > settings.max_file_size_bytes:
                    raise ValueError("workspace file too large")
        return self


class ExecuteRequest(BaseModel):
    execution_type: ExecutionType
    command: str | None = Field(default=None, max_length=10_000)
    code: str | None = Field(default=None, max_length=1_000_000)
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    working_directory: str | None = "/workspace"
    environment: dict[str, str] | None = None
    stdin_data: str | None = Field(default=None, max_length=1_000_000)

    @model_validator(mode="after")
    def _validate_inputs(self) -> "ExecuteRequest":
        if bool(self.command) == bool(self.code):
            raise ValueError("exactly one of command/code is required")
        blocked = ["docker", "nsenter", "chroot", "mount", "/proc/", "/sys/"]
        if self.command and any(b in self.command for b in blocked):
            raise ValueError("command contains blocked token")
        if self.working_directory and not (self.working_directory.startswith("/workspace") or self.working_directory.startswith("/tmp")):
            raise ValueError("working_directory must be under /workspace or /tmp")
        if self.working_directory and ".." in self.working_directory:
            raise ValueError("working_directory cannot contain ..")
        return self


class WriteFilesRequest(BaseModel):
    files: dict[str, str]

    @model_validator(mode="after")
    def _validate(self) -> "WriteFilesRequest":
        if not (1 <= len(self.files) <= 100):
            raise ValueError("files must contain 1..100 entries")
        total = 0
        for path, content in self.files.items():
            if path.startswith("/") or ".." in path:
                raise ValueError("invalid file path")
            size = len(content.encode("utf-8"))
            if size > settings.max_file_size_bytes:
                raise ValueError("file too large")
            total += size
        if total > 100 * 1024 * 1024:
            raise ValueError("total file payload too large")
        return self


class InstallDependenciesRequest(BaseModel):
    packages: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _validate(self) -> "InstallDependenciesRequest":
        blocked = set(";|&`$(){}")
        for pkg in self.packages:
            if any(ch in pkg for ch in blocked):
                raise ValueError("package contains blocked shell characters")
        return self


SANDBOXES: dict[str, dict[str, Any]] = {}
EXECUTIONS: dict[str, dict[str, Any]] = {}


def _workspace(sandbox_id: str) -> Path:
    base = Path(settings.workspace_base if settings.workspace_base else "/tmp/omni-sandboxes")
    if str(base).startswith("/workspaces"):
        base = Path("/tmp/omni-sandboxes")
    target = base / sandbox_id
    target.mkdir(parents=True, exist_ok=True)
    return target


async def _write_file(root: Path, path: str, content: str) -> None:
    file_path = root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(content)


@router.post("/api/v1/sandboxes")
async def create_sandbox(request: CreateSandboxRequest) -> dict[str, Any]:
    active = sum(1 for sbx in SANDBOXES.values() if sbx["status"] != SandboxStatus.DESTROYED)
    if active >= settings.max_concurrent_sandboxes:
        raise HTTPException(status_code=429, detail="max concurrent sandboxes reached")

    sandbox_id = f"sbx-{uuid.uuid4().hex[:12]}"
    workspace = _workspace(sandbox_id)
    if request.workspace_files:
        for path, content in request.workspace_files.items():
            await _write_file(workspace, path, content)

    now = datetime.now(timezone.utc)
    payload = {
        "sandbox_id": sandbox_id,
        "task_id": request.task_id,
        "language": request.language.value,
        "status": SandboxStatus.READY,
        "workspace_path": str(workspace),
        "container_id": f"sim-{sandbox_id}",
        "container_name": f"omni-sandbox-{sandbox_id}",
        "resource_limits": {
            "memory_limit": request.memory_limit or settings.default_memory_limit,
            "cpu_limit": request.cpu_limit or settings.default_cpu_limit,
        },
        "network_mode": request.network_mode or settings.sandbox_network,
        "execution_count": 0,
        "created_at": now.isoformat(),
        "last_activity_at": now.isoformat(),
        "ttl_seconds": request.ttl_seconds or settings.sandbox_ttl_seconds,
        "dependencies": request.dependencies,
    }
    SANDBOXES[sandbox_id] = payload
    return payload


@router.get("/api/v1/sandboxes")
async def list_sandboxes() -> dict[str, Any]:
    sandboxes = list(SANDBOXES.values())
    by_language: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for sbx in sandboxes:
        by_language[sbx["language"]] = by_language.get(sbx["language"], 0) + 1
        status = str(sbx["status"])
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "sandboxes": sandboxes,
        "total": len(sandboxes),
        "active": sum(1 for s in sandboxes if s["status"] != SandboxStatus.DESTROYED),
        "by_language": by_language,
        "by_status": by_status,
    }


@router.get("/api/v1/sandboxes/stats")
async def stats() -> dict[str, Any]:
    executions = list(EXECUTIONS.values())
    durations = [e["duration_ms"] for e in executions]
    avg = sum(durations) / len(durations) if durations else 0.0
    p95 = sorted(durations)[int(len(durations) * 0.95) - 1] if durations else 0.0
    return {
        "total_created": len(SANDBOXES),
        "total_destroyed": sum(1 for s in SANDBOXES.values() if s["status"] == SandboxStatus.DESTROYED),
        "currently_active": sum(1 for s in SANDBOXES.values() if s["status"] != SandboxStatus.DESTROYED),
        "total_executions": len(executions),
        "avg_duration_ms": round(avg, 2),
        "p95_duration_ms": round(float(p95), 2),
    }


@router.get("/api/v1/sandboxes/{sandbox_id}")
async def get_sandbox(sandbox_id: str) -> dict[str, Any]:
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    return sbx


@router.post("/api/v1/sandboxes/{sandbox_id}/files")
async def write_files(sandbox_id: str, request: WriteFilesRequest) -> dict[str, Any]:
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    root = Path(sbx["workspace_path"])
    total = 0
    for path, content in request.files.items():
        await _write_file(root, path, content)
        total += len(content.encode("utf-8"))
    sbx["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    return {"sandbox_id": sandbox_id, "files_written": len(request.files), "bytes_written": total}


@router.get("/api/v1/sandboxes/{sandbox_id}/files")
async def list_files(sandbox_id: str) -> dict[str, Any]:
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    root = Path(sbx["workspace_path"])
    files = []
    total_size = 0
    for path in root.rglob("*"):
        if path.is_file():
            stat = path.stat()
            rel = path.relative_to(root).as_posix()
            files.append({
                "path": rel,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "file_type": "file",
                "permissions": oct(stat.st_mode & 0o777),
            })
            total_size += stat.st_size
    return {"sandbox_id": sandbox_id, "files": files, "total_files": len(files), "total_size_bytes": total_size}


@router.get("/api/v1/sandboxes/{sandbox_id}/files/{path:path}")
async def read_file(sandbox_id: str, path: str) -> dict[str, Any]:
    if path.startswith("/") or ".." in path:
        raise HTTPException(status_code=422, detail="invalid path")
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    file_path = Path(sbx["workspace_path"]) / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    content = file_path.read_text(encoding="utf-8")
    return {
        "sandbox_id": sandbox_id,
        "path": path,
        "content": content,
        "size_bytes": len(content.encode("utf-8")),
        "encoding": "utf-8",
    }


@router.post("/api/v1/sandboxes/{sandbox_id}/dependencies")
async def install_dependencies(sandbox_id: str, request: InstallDependenciesRequest) -> dict[str, Any]:
    if sandbox_id not in SANDBOXES:
        raise HTTPException(status_code=404, detail="sandbox not found")
    results = []
    for pkg in request.packages:
        results.append({"package": pkg, "installed": True, "version": pkg.split("==")[-1] if "==" in pkg else None, "error": None})
    return {
        "sandbox_id": sandbox_id,
        "packages_requested": len(request.packages),
        "results": results,
        "all_succeeded": all(r["installed"] for r in results),
        "install_log": "simulated install",
        "duration_ms": 10.0 * len(request.packages),
    }


def _language_command(language: str, code_path: Path) -> list[str]:
    if language.startswith("python"):
        return ["python", str(code_path)]
    if language.startswith("node"):
        return ["node", str(code_path)]
    if language.startswith("ruby"):
        return ["ruby", str(code_path)]
    return ["python", str(code_path)]


@router.post("/api/v1/sandboxes/{sandbox_id}/execute")
async def execute(sandbox_id: str, request: ExecuteRequest) -> dict[str, Any]:
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    if sbx["status"] == SandboxStatus.EXECUTING:
        raise HTTPException(status_code=409, detail="sandbox is busy")

    sbx["status"] = SandboxStatus.EXECUTING
    started = time.perf_counter()
    exec_id = f"exec-{uuid.uuid4().hex[:12]}"
    root = Path(sbx["workspace_path"])

    command_list: list[str]
    temp_file: Path | None = None
    if request.code:
        suffix = ".py" if sbx["language"].startswith("python") else ".txt"
        temp_file = root / f"_omni_exec_{exec_id}{suffix}"
        temp_file.write_text(request.code, encoding="utf-8")
        command_list = _language_command(sbx["language"], temp_file)
        command = " ".join(command_list)
    else:
        command = request.command or ""
        command_list = ["sh", "-c", command]

    try:
        proc = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                command_list,
                cwd=root,
                input=request.stdin_data,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                env=None,
            ),
            timeout=request.timeout_seconds + 1,
        )
        timed_out = False
        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = 124
        stdout = ""
        stderr = "execution timed out"
    except asyncio.TimeoutError:
        timed_out = True
        exit_code = 124
        stdout = ""
        stderr = "execution timed out"

    duration_ms = (time.perf_counter() - started) * 1000
    stdout = stdout[: settings.max_output_bytes]
    stderr = stderr[: settings.max_output_bytes]

    result = {
        "execution_id": exec_id,
        "sandbox_id": sandbox_id,
        "execution_type": request.execution_type,
        "command": command,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "duration_ms": round(duration_ms, 2),
        "timed_out": timed_out,
        "resource_usage": {
            "memory_mb": 0,
            "memory_limit_mb": 0,
            "memory_percent": 0,
            "cpu_percent": 0,
            "disk_usage_mb": 0,
            "pids": 1,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    EXECUTIONS[exec_id] = result
    sbx["execution_count"] += 1
    sbx["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    sbx["status"] = SandboxStatus.READY
    if temp_file and temp_file.exists():
        temp_file.unlink(missing_ok=True)
    return result


@router.get("/api/v1/sandboxes/{sandbox_id}/executions")
async def list_executions(sandbox_id: str) -> list[dict[str, Any]]:
    if sandbox_id not in SANDBOXES:
        raise HTTPException(status_code=404, detail="sandbox not found")
    return [e for e in EXECUTIONS.values() if e["sandbox_id"] == sandbox_id]


@router.get("/api/v1/sandboxes/{sandbox_id}/executions/{execution_id}")
async def get_execution(sandbox_id: str, execution_id: str) -> dict[str, Any]:
    data = EXECUTIONS.get(execution_id)
    if not data or data["sandbox_id"] != sandbox_id:
        raise HTTPException(status_code=404, detail="execution not found")
    return data


@router.delete("/api/v1/sandboxes/{sandbox_id}")
async def destroy_sandbox(sandbox_id: str) -> dict[str, Any]:
    sbx = SANDBOXES.get(sandbox_id)
    if not sbx:
        raise HTTPException(status_code=404, detail="sandbox not found")
    sbx["status"] = SandboxStatus.DESTROYED
    return {"sandbox_id": sandbox_id, "status": "destroyed"}


@router.websocket("/ws/sandboxes/{sandbox_id}/stream")
async def stream_execution(websocket: WebSocket, sandbox_id: str) -> None:
    await websocket.accept()
    if sandbox_id not in SANDBOXES:
        await websocket.send_json({"type": "error", "message": "sandbox not found"})
        await websocket.close(code=1008)
        return
    try:
        while True:
            payload = await websocket.receive_json()
            action = payload.get("action")
            if action != "execute":
                await websocket.send_json({"type": "error", "message": "unsupported action"})
                continue
            command = payload.get("command", "echo stream")
            start = time.perf_counter()
            proc = subprocess.run(["sh", "-c", command], capture_output=True, text=True)
            if proc.stdout:
                for line in proc.stdout.splitlines():
                    await websocket.send_json({"type": "stdout", "data": line, "timestamp": datetime.now(timezone.utc).isoformat()})
            if proc.stderr:
                for line in proc.stderr.splitlines():
                    await websocket.send_json({"type": "stderr", "data": line, "timestamp": datetime.now(timezone.utc).isoformat()})
            await websocket.send_json({
                "type": "exit",
                "exit_code": proc.returncode,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
            })
    except WebSocketDisconnect:
        return
