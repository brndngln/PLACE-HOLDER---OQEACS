from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from src.models import CommandResult, GenerateRequest, ReviewRequest
from src.services.code_client import CodeClient
from src.services.command_registry import CommandRegistry

router = APIRouter(prefix="/api/v1", tags=["cli"])
_registry = CommandRegistry()


@router.get("/commands")
def commands():
    return _registry.list_commands()


@router.post("/execute", response_model=CommandResult)
async def execute(payload: dict) -> CommandResult:
    command = payload.get("command")
    start = time.perf_counter()
    spec = _registry.get_command(command)
    if not spec:
        raise HTTPException(status_code=404, detail="Unknown command")

    client = CodeClient()
    output = ""
    error = None
    success = True

    try:
        if command == "generate":
            output = await client.generate(GenerateRequest(**payload["args"]))
        elif command == "review":
            output = str(await client.review(ReviewRequest(**payload["args"])))
        elif command == "test":
            output = str(await client.test(payload["args"]["file_path"]))
        elif command == "debug":
            output = str(await client.debug(payload["args"]["error"]))
        else:
            output = f"Executed command: {command}"
    except Exception as exc:
        success = False
        error = str(exc)

    elapsed = (time.perf_counter() - start) * 1000
    return CommandResult(command=command, success=success, output=output, duration_ms=round(elapsed, 2), error=error)
