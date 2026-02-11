from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.exceptions import ServiceError
from app.models import (
    WorkflowDefinition,
    WorkflowDefinitionCreate,
    WorkflowRun,
    WorkflowSignalRequest,
    WorkflowStartRequest,
    WorkflowStats,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TemporalControlPlane:
    def __init__(self, data_path: str, max_concurrent_runs: int) -> None:
        self._data_path = Path(data_path)
        self._max_concurrent_runs = max_concurrent_runs
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._runs: dict[str, WorkflowRun] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._data_path.exists():
            return
        payload = json.loads(self._data_path.read_text(encoding="utf-8"))
        self._definitions = {
            item["id"]: WorkflowDefinition.model_validate(item) for item in payload.get("definitions", [])
        }
        self._runs = {
            item["id"]: WorkflowRun.model_validate(item) for item in payload.get("runs", [])
        }

    async def _persist(self) -> None:
        payload = {
            "definitions": [d.model_dump(mode="json") for d in self._definitions.values()],
            "runs": [r.model_dump(mode="json") for r in self._runs.values()],
        }
        self._data_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    async def register_definition(self, request: WorkflowDefinitionCreate) -> WorkflowDefinition:
        async with self._lock:
            definition = WorkflowDefinition(
                id=f"wfd-{uuid4().hex[:12]}",
                name=request.name,
                task_queue=request.task_queue,
                workflow_type=request.workflow_type,
                input_schema=request.input_schema,
                created_at=_utcnow(),
            )
            self._definitions[definition.id] = definition
            await self._persist()
            return definition

    async def start_run(self, request: WorkflowStartRequest) -> WorkflowRun:
        async with self._lock:
            if request.definition_id not in self._definitions:
                raise ServiceError("workflow definition not found", status_code=404, code="definition_not_found")

            running = sum(1 for run in self._runs.values() if run.status == "running")
            if running >= self._max_concurrent_runs:
                raise ServiceError("max concurrent runs exceeded", status_code=429, code="capacity_exceeded")

            run = WorkflowRun(
                id=f"wrk-{uuid4().hex[:12]}",
                definition_id=request.definition_id,
                status="queued",
                input_payload=request.input_payload,
                created_at=_utcnow(),
            )
            self._runs[run.id] = run
            self._tasks[run.id] = asyncio.create_task(self._simulate_run(run.id, request.timeout_seconds))
            await self._persist()
            return run

    async def _simulate_run(self, run_id: str, timeout_seconds: int) -> None:
        try:
            async with self._lock:
                run = self._runs[run_id]
                run.status = "running"
                run.started_at = _utcnow()
                await self._persist()

            await asyncio.sleep(min(2.0, max(0.1, timeout_seconds / 1000.0)))

            async with self._lock:
                run = self._runs[run_id]
                run.status = "completed"
                run.result = {
                    "message": "workflow completed in simulated execution mode",
                    "echo": run.input_payload,
                }
                run.ended_at = _utcnow()
                await self._persist()
        except asyncio.CancelledError:
            async with self._lock:
                run = self._runs.get(run_id)
                if run:
                    run.status = "terminated"
                    run.error = "terminated by control plane"
                    run.ended_at = _utcnow()
                    await self._persist()
            raise
        except Exception as exc:
            async with self._lock:
                run = self._runs.get(run_id)
                if run:
                    run.status = "failed"
                    run.error = str(exc)
                    run.ended_at = _utcnow()
                    await self._persist()

    async def list_definitions(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())

    async def list_runs(self) -> list[WorkflowRun]:
        return sorted(self._runs.values(), key=lambda item: item.created_at, reverse=True)

    async def get_run(self, run_id: str) -> WorkflowRun:
        run = self._runs.get(run_id)
        if not run:
            raise ServiceError("workflow run not found", status_code=404, code="run_not_found")
        return run

    async def signal_run(self, run_id: str, request: WorkflowSignalRequest) -> WorkflowRun:
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise ServiceError("workflow run not found", status_code=404, code="run_not_found")
            run.signals.append(
                {
                    "signal_name": request.signal_name,
                    "payload": request.payload,
                    "received_at": _utcnow().isoformat(),
                }
            )
            await self._persist()
            return run

    async def terminate_run(self, run_id: str) -> WorkflowRun:
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise ServiceError("workflow run not found", status_code=404, code="run_not_found")
            task = self._tasks.get(run_id)
            if task and not task.done():
                task.cancel()
            run.status = "terminated"
            run.ended_at = _utcnow()
            await self._persist()
            return run

    async def stats(self) -> WorkflowStats:
        runs = list(self._runs.values())
        return WorkflowStats(
            total_definitions=len(self._definitions),
            total_runs=len(runs),
            running_runs=sum(1 for run in runs if run.status == "running"),
            completed_runs=sum(1 for run in runs if run.status == "completed"),
            failed_runs=sum(1 for run in runs if run.status == "failed"),
        )


async def check_temporal_reachable(address: str) -> tuple[bool, str]:
    host, sep, port_str = address.partition(":")
    if not sep:
        return False, "invalid temporal address"
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port_str)), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        _ = reader
        return True, "ok"
    except Exception as exc:
        return False, str(exc)
